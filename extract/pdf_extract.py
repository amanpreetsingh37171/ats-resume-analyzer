import pdfplumber
import io
import pytesseract
from PIL import Image


def extract_text_from_pdf(uploaded_file):
    """Extract text from a PDF file-like. If selectable text is not found (image-only PDF),
    fall back to rendering pages to images and running OCR (pytesseract).

    `uploaded_file` can be a Streamlit `UploadedFile` or any file-like object.
    """
    text = ''
    # Try opening directly with pdfplumber
    try:
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ''
                if page_text:
                    text += page_text + '\n'
    except Exception:
        # fallback: read bytes and reopen via BytesIO
        try:
            uploaded_file.seek(0)
            bytes_data = uploaded_file.read()
            with pdfplumber.open(io.BytesIO(bytes_data)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text() or ''
                    if page_text:
                        text += page_text + '\n'
        except Exception:
            # if even reopening fails, re-raise to be handled by caller
            raise

    # If pdfplumber returned no or very little text, attempt OCR on each page
    if not text.strip():
        try:
            # ensure we have a BytesIO to reopen
            try:
                uploaded_file.seek(0)
                bytes_data = uploaded_file.read()
                bio = io.BytesIO(bytes_data)
            except Exception:
                # if uploaded_file is already a bytes-like object
                bio = io.BytesIO(uploaded_file)

            with pdfplumber.open(bio) as pdf:
                ocr_text = ''
                for page in pdf.pages:
                    # render page to an image (Pillow) and OCR it
                    try:
                        # pdfplumber's to_image requires pdfplumber v0.5+, and will produce a PIL image
                        page_image = page.to_image(resolution=150)
                        pil_img = page_image.original
                        if isinstance(pil_img, Image.Image):
                            page_ocr = pytesseract.image_to_string(pil_img)
                            if page_ocr:
                                ocr_text += page_ocr + '\n'
                    except Exception:
                        # fallback: try to get the raw image bytes via cropping the page bbox
                        try:
                            pil_img = page.to_image().original
                            page_ocr = pytesseract.image_to_string(pil_img)
                            if page_ocr:
                                ocr_text += page_ocr + '\n'
                        except Exception:
                            continue
                if ocr_text:
                    text = ocr_text
        except Exception:
            # if OCR fails, return whatever text we have (likely empty)
            pass

    return text