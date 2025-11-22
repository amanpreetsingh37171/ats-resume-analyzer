import pdfplumber
import io

def extract_text_from_pdf(uploaded_file):
    # uploaded_file is a stream-like object provided by Streamlit
    text = ''
    try:
        # pdfplumber can accept a file-like object
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + '\n'
    except Exception as e:
        # fallback: try reading bytes and reopen via io.BytesIO
        try:
            uploaded_file.seek(0)
            bytes_data = uploaded_file.read()
            with pdfplumber.open(io.BytesIO(bytes_data)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + '\n'
        except Exception:
            raise
    return text