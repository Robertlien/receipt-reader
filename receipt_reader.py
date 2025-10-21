import streamlit as st
import requests
from PIL import Image
import io

st.title("🧾 Free Receipt Reader")

uploaded_file = st.file_uploader("Upload a receipt image", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Receipt", use_container_width=True)

    # Use OCR.Space free API (no key needed for demo)
    url_api = "https://api.ocr.space/parse/image"
    api_key = st.secrets["OCR_SPACE_API_KEY"]  # 🔑 <-- Replace this

    payload = {
        "language": "eng",
        "apikey": api_key,
        "OCREngine": 2
    }
    files = {
        "file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)
    }

    with st.spinner("Reading text..."):
        response = requests.post(url_api, files=files, data=payload)
        result = response.json()

    try:
        parsed_text = result["ParsedResults"][0]["ParsedText"]
        st.subheader("Extracted Text:")
        st.text(parsed_text)
    except Exception as e:
        st.error("Could not read text. Please try another image.")
