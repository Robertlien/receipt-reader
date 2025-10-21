import streamlit as st
import requests
from PIL import Image
import io

st.title("🧾 Free Receipt Reader")

uploaded_file = st.file_uploader("Upload a receipt image", type=["png", "jpg", "jpeg"])

def compress_image(image, max_size_kb=1024, max_width=1600):
    """Resize and compress image to stay under max_size_kb."""
    # Resize if width is too large
    if image.width > max_width:
        ratio = max_width / float(image.width)
        new_height = int(image.height * ratio)
        image = image.resize((max_width, new_height))

    # Compress iteratively
    quality = 90
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=quality)
    while buffer.tell() / 1024 > max_size_kb and quality > 20:
        quality -= 10
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=quality)
    buffer.seek(0)
    return buffer

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Receipt", use_container_width=True)

    # Compress before sending
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
                st.subheader("Extracted Text:")
                st.text(parsed_text)

        except requests.exceptions.RequestException as e:
            st.error(f"⚠️ Network or API error: {e}")
        except Exception as e:
            st.error(f"⚠️ Unexpected error: {e}")
else:
    st.info("📤 Please upload a receipt image to start.")
