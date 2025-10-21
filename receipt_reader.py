import streamlit as st
import requests
from PIL import Image

st.title("🧾 Free Receipt Reader")

uploaded_file = st.file_uploader("Upload a receipt image", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Receipt", use_column_width=True)

    url_api = "https://api.ocr.space/parse/image"
    api_key = st.secrets.get("OCR_SPACE_API_KEY", "")  # safer: uses Streamlit secrets

    payload = {
        "language": "eng",
        "apikey": api_key,
        "OCREngine": 2
    }

    files = {
        "file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)
    }

    with st.spinner("Reading text..."):
        try:
            response = requests.post(url_api, files=files, data=payload, timeout=60)
            result = response.json()

            # Check for OCR errors
            if result.get("IsErroredOnProcessing"):
                error_msg = result.get("ErrorMessage", "Unknown error occurred.")
                st.error(f"❌ OCR failed: {error_msg}")
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

