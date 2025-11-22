from PIL import Image
import pytesseract
import io

def extract_text_from_image(uploaded_file):
    uploaded_file.seek(0)
    image = Image.open(uploaded_file).convert('RGB')
    text = pytesseract.image_to_string(image)
    return text
