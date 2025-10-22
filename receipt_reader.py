import streamlit as st
import pandas as pd
import requests
from PIL import Image
import io
import re

st.title("🧾 Receipt Reader")
with st.expander("Select OCR API 🔑", expanded=False):
    selected_key = st.radio(
        "Select API Key",  # Add a small label (optional)
        ("Key 1", "Key 2"),
        label_visibility="collapsed",  # hides the label to remove space
        horizontal=True
    )

    if selected_key == "Key 1":
        api_key = st.secrets["OCR_SPACE_API_KEY_1"]
    else:
        api_key = st.secrets["OCR_SPACE_API_KEY_2"]

    st.markdown(f"**_{selected_key} activated_**")
uploaded_file = st.file_uploader("", help="Please upload an image file under 1 MB.")


def compress_image(image, max_size_kb=1024, max_width=1600):
    if image.width > max_width:
        ratio = max_width / float(image.width)
        new_height = int(image.height * ratio)
        image = image.resize((max_width, new_height))

    quality = 90
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=quality)
    while buffer.tell() / 1024 > max_size_kb and quality > 20:
        quality -= 10
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=quality)
    buffer.seek(0)
    return buffer

def parse_receipt_safe_total(result, height_tolerance=10):
    """Parse OCR receipt results into structured data (date/time, items, total)."""
    parsed = result.get("ParsedResults", [{}])[0]
    lines = parsed.get("TextOverlay", {}).get("Lines", [])

    # === Regex patterns ===
    date_pattern  = r"\b\d{1,2}/\d{1,2}/\d{4}\b"
    time_pattern  = r"\b\d{1,2}:\d{2}:\d{2}(?:\s*[APMapm]{2})?\b"
    price_pattern = r"(-?\$|\$-)\s*([\d,.]+)"

    # === Build DataFrame from OCR overlay ===
    rows = [
        {
            "text": line["LineText"],
            "top": min(w["Top"] for w in line["Words"]),
            "left": min(w["Left"] for w in line["Words"]),
        }
        for line in lines if line.get("LineText")
    ]
    if not rows:
        return "", [], "", pd.DataFrame()

    df = pd.DataFrame(rows).sort_values(["top", "left"]).reset_index(drop=True)

    # === Group lines with similar vertical position ===
    grouped_lines, current_group, current_top = [], [], None
    for _, row in df.iterrows():
        if current_top is None or abs(row["top"] - current_top) <= height_tolerance:
            current_group.append(row)
            current_top = row["top"] if current_top is None else current_top
        else:
            merged_text = " ".join(
                [r["text"] for r in sorted(current_group, key=lambda x: x["left"])]
            )
            grouped_lines.append({"text": merged_text, "top": current_top})
            current_group, current_top = [row], row["top"]

    # Add the final group
    if current_group:
        merged_text = " ".join(
            [r["text"] for r in sorted(current_group, key=lambda x: x["left"])]
        )
        grouped_lines.append({"text": merged_text, "top": current_top})

    grouped_df = pd.DataFrame(grouped_lines).sort_values("top")

    # === Extract date/time ===
    date_time = ""
    for text in grouped_df["text"]:
        date_match = re.search(date_pattern, text)
        time_match = re.search(time_pattern, text)
        if date_match or time_match:
            date_time = f"{date_match.group() if date_match else ''} {time_match.group() if time_match else ''}".strip()
            break

    # === Extract items + prices ===
    items, total_price, previous_item = [], "", ""
    for _, row in grouped_df.iterrows():
        line = row["text"]
        price_match = re.search(price_pattern, line)
        if not price_match:
            previous_item = line
            continue

        parts = re.split(price_pattern, line)
        item_name = parts[0].strip() or previous_item

        # Normalize sign and format price
        sign = "-" if "-" in price_match.group(1) else ""
        price = f"{sign}${price_match.group(2)}"

        items.append({"Item": item_name, "Price": price})
        previous_item = item_name

        # Stop if "Order Total" line is found
        if re.search(r"order\s*total", item_name, re.IGNORECASE):
            total_price = price
            break

    return date_time, items, total_price, grouped_df




if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Receipt", use_container_width=True)

    compressed_image = compress_image(image)
    compressed_size = len(compressed_image.getvalue()) / 1024
    st.caption(f"📦 Compressed image size: {compressed_size:.1f} KB")
    
    url_api = "https://api.ocr.space/parse/image"

    payload = {
        "language": "eng",
        "apikey": api_key,
        "OCREngine": 2,
        "detectOrientation": True,
        "IsOverlayRequired": True
    }

    files = {
        "file": ("compressed.jpg", compressed_image.getvalue(), "image/jpeg")
    }

    with st.spinner("Reading text..."):
        try:
            response = requests.post(url_api, files=files, data=payload, timeout=60)
            result = response.json()

            if result.get("IsErroredOnProcessing"):
                error_msg = result.get("ErrorMessage", "Unknown error occurred.")
                st.error(f"❌ OCR failed: {error_msg}")
                with st.expander("See full API response"):
                    st.json(result)
            else:
                pass

                # Parse receipt safely with total check
                date_time, items, total_price, grouped_df = parse_receipt_safe_total(result)

                st.subheader("Receipt Summary:")
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown(
                        f"<h4 style='font-size:18px;'>Date/Time: "
                        f"{date_time if date_time else 'Unknown'}</h4>",
                        unsafe_allow_html=True
                    )
                
                with col2:
                    if total_price:
                        st.markdown(
                            f"<h4 style='font-size:22px; text-align:right;'>💰 Total: {total_price}</h4>",
                            unsafe_allow_html=True
                        )
                if items:
                    st.table(items)
                    
                # Toggle to show original OCR text
                with st.expander("Show original OCR text"):
                    st.subheader("Full OCR Text:")
                    st.text(grouped_df)

        except requests.exceptions.RequestException as e:
            st.error(f"⚠️ Network or API error: {e}")
        except Exception as e:
            st.error(f"⚠️ Unexpected error: {e}")
else:
    st.info("📤 Please upload a receipt image to start.")

