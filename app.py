from dotenv import load_dotenv
load_dotenv()

import streamlit as st
import os
from PIL import Image
import google.generativeai as genai
import time
from google.api_core.exceptions import ResourceExhausted
from pdf2image import convert_from_bytes
import io

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-2.5-pro')

def get_gemini_response(prompt, image_data, input_text, max_retries=3, rate_limit_delay=2):
    content_payload = [prompt, input_text] + image_data
    for attempt in range(max_retries):
        try:
            time.sleep(rate_limit_delay)
            response = model.generate_content(content_payload)
            return response.text
        except ResourceExhausted:
            wait_time = (2 ** attempt) * 10
            st.warning(f"⚠️ Quota exceeded. Retrying in {wait_time} seconds... (attempt {attempt+1}/{max_retries})")
            time.sleep(wait_time)
        except Exception as e:
            st.error(f"An error occurred: {e}")
            return None
    st.error("🚫 Daily/Free-tier quota exhausted. Please try again later or upgrade your plan.")
    return None

def input_image_details(file_bytes, file_type):
    if not file_bytes:
        raise ValueError("Uploaded file is empty!")

    if file_type == "application/pdf":
        images = convert_from_bytes(file_bytes)
        image_parts = []
        for image in images:
            buf = io.BytesIO()
            image.save(buf, format="JPEG")
            image_parts.append({"mime_type": "image/jpeg", "data": buf.getvalue()})
        return image_parts
    else:
        return [{"mime_type": file_type, "data": file_bytes}]

# Streamlit UI
st.set_page_config(page_title="Multilanguage Invoice Extractor")
st.header("📄 Multilanguage Invoice Extractor")
input_text = st.text_input("Type your query here:", key="input")

uploaded_file = st.file_uploader(
    "Choose an image or PDF of the invoice...",
    type=["jpg", "jpeg", "png", "pdf"]
)

file_bytes = None
if uploaded_file is not None:
    file_bytes = uploaded_file.getvalue()
    if not file_bytes:
        st.error("Uploaded file is empty.")
    else:
        if uploaded_file.type == "application/pdf":
            st.info("Displaying the first page of the uploaded PDF.")
            preview_image = convert_from_bytes(file_bytes, first_page=1, last_page=1)[0]
            st.image(preview_image, caption="PDF First Page Preview.", width="stretch")
        else:
            image = Image.open(io.BytesIO(file_bytes))
            st.image(image, caption="Uploaded Image.", width="stretch")

submit = st.button("Extract Invoice Details")

input_prompt = """
You are an expert in understanding invoices. We will upload an image as invoice
and you will have to answer any questions based on the uploaded invoice image.
"""

if submit:
    if uploaded_file is not None and file_bytes:
        with st.spinner('Analyzing the document...'):
            image_data = input_image_details(file_bytes, uploaded_file.type)
            response = get_gemini_response(input_prompt, image_data, input_text)
            st.subheader("Here’s what I found:")
            st.write(response)
    else:
        st.error("Please upload a file first.")
