import streamlit as st
import requests
from PIL import Image
import io
import re

st.title("🧾 Receipt Reader")

uploaded_file = st.file_uploader("", help="Please upload an image file under 1 MB.")

def compress_image(image, max_size_kb=1024, max_width=1600):
    """Resize and compress image to stay under max_size_kb."""
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

def parse_receipt_by_dollar(text):
    """Parse receipt text by looking for $ prices."""
    lines = text.splitlines()
    items = []
    total_price = ""
    date_time = ""
    
    # Simple date/time regex
    date_pattern = r"\b\d{2}[/-]\d{2}[/-]\d{2,4}\b"
    time_pattern = r"\b\d{1,2}:\d{2}\b"
    
    for line in lines:
        # Date/time
        if not date_time:
            date_match = re.search(date_pattern, line)
            time_match = re.search(time_pattern, line)
            if date_match or time_match:
                date_time = f"{date_match.group() if date_match else ''} {time_match.group() if time_match else ''}".strip()
        
        # Look for $ in line
        if "$" in line:
            parts = line.split("$")
            item_name = parts[0].strip()
            price = parts[1].strip() if len(parts) > 1 else ""
            items.append({"Item": item_name, "Price": f"${price}"})
            
            # Check if this line is total
            if re.search(r"total", line, re.IGNORECASE):
                total_price = f"${price}"
    
    return date_time, items, total_price

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Receipt", use_container_width=True)

    compressed_image = compress_image(image)
    compressed_size = len(compressed_image.getvalue()) / 1024
    st.write(f"📦 Compressed image size: {compressed_size:.1f} KB")

    url_api = "https://api.ocr.space/parse/image"
    api_key = st.secrets.get("OCR_SPACE_API_KEY", "")

    payload = {
        "language": "eng",
        "apikey": api_key,
        "OCREngine": 2
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
                parsed_text = result["ParsedResults"][0]["ParsedText"]

                # Toggle to show original OCR text
                if st.checkbox("Show original OCR text"):
                    st.subheader("Full OCR Text:")
                    st.text(parsed_text)

                # Parse receipt by $ sign
                date_time, items, total_price = parse_receipt_by_dollar(parsed_text)

                st.subheader("Receipt Summary:")
                st.write(f"**Date/Time:** {date_time if date_time else 'Unknown'}")
                
                if items:
                    st.table(items)
                
                if total_price:
                    st.write(f"**Total:** {total_price}")

        except requests.exceptions.RequestException as e:
            st.error(f"⚠️ Network or API error: {e}")
        except Exception as e:
            st.error(f"⚠️ Unexpected error: {e}")
else:
    st.info("📤 Please upload a receipt image to start.")
