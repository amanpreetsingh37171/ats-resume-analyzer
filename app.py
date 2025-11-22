import sys
from pathlib import Path

# ensure repository root is on sys.path so local packages like `models` and `utils` can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st
# try import from the local package — support both `model` and `models` directories
try:
    from model.predict import Predictor
except Exception:
    try:
        from model.predict import Predictor
    except Exception:
        # fallback: load Predictor directly from an expected file path
        import importlib.util
        base = Path(__file__).resolve().parent
        candidate = None
        for sub in ('model', 'models'):
            p = base / sub / 'predict.py'
            if p.exists():
                candidate = p
                break
        if candidate is None:
            raise ImportError('Could not find predict.py in model/ or models/ folders')
        spec = importlib.util.spec_from_file_location('predictor_module', str(candidate))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        Predictor = mod.Predictor
from extract.pdf_extract import extract_text_from_pdf
from extract.image_extract import extract_text_from_image
from utils.clean import clean_text
from utils.suggestions import generate_suggestions, generate_deep_suggestions
import io

st.set_page_config(page_title='ATS Resume Analyzer', layout='wide')
st.title('ATS Resume Analyzer')

st.sidebar.header('Options')
uploaded_file = st.sidebar.file_uploader('Upload resume (pdf / png / jpg)', type=['pdf','png','jpg','jpeg'])
upload_model = st.sidebar.file_uploader('(Optional) Upload trained artifacts zip (model + vectorizer)', type=['zip'])
# Always render the Extract & Predict button (so it appears in the deployed app UI). We
# capture the click into `extract_button` and use it below only when a file is uploaded.
extract_button = st.sidebar.button('Extract & Predict')
run_button = st.sidebar.button('Load model / Predict')

# Auto-detect artifacts directory on startup so model is always available when the app runs.
base = Path(__file__).resolve().parent
candidate_dirs = [
    base / 'artifacts',
    base / 'model' / 'artifacts',
    base / 'models' / 'artifacts',
]
detected = None
for d in candidate_dirs:
    if d.exists():
        detected = d
        break

if detected is None:
    # also check for artifacts inside a nested package (common when running from different cwd)
    possible = list(base.rglob('artifacts'))
    if possible:
        detected = possible[0]

if detected is None:
    artifacts_dir = str(base / 'artifacts')
else:
    artifacts_dir = str(detected)

predictor = Predictor(artifacts_dir=artifacts_dir)

# Sidebar status + reload control
with st.sidebar.expander('Model status', expanded=True):
    st.write(f'Artifacts path: `{artifacts_dir}`')
    if predictor.ready:
        st.success('Model loaded and ready')
    else:
        st.warning('No artifacts found at path — model not ready')
    if st.button('Reload model'):
        predictor = Predictor(artifacts_dir=artifacts_dir)
        if predictor.ready:
            st.success('Model reloaded successfully')
        else:
            st.error('Reload failed — no artifacts found or load error')

if upload_model is not None:
    st.sidebar.info('You uploaded an artifacts zip — extracting to artifacts folder')
    import zipfile, tempfile, shutil
    tmp = tempfile.NamedTemporaryFile(delete=False)
    tmp.write(upload_model.read())
    tmp.flush()
    with zipfile.ZipFile(tmp.name, 'r') as z:
        # extract into the detected artifacts dir (or default)
        target = Path(artifacts_dir)
        target.mkdir(parents=True, exist_ok=True)
        z.extractall(str(target))
    st.sidebar.success(f'Artifacts extracted to `{artifacts_dir}`.')
    # reload predictor to pick up newly extracted files
    predictor = Predictor(artifacts_dir=artifacts_dir)
    if predictor.ready:
        st.sidebar.success('Model loaded and ready')
    else:
        st.sidebar.error('Artifacts extracted but model failed to load; check files.')

if uploaded_file is None:
    st.sidebar.info('Upload a resume file to enable the Extract & Predict action.')

if uploaded_file is not None and extract_button:
    # extract text
    text = ''
    # Read raw bytes once — mobile browsers sometimes omit or set incorrect MIME types,
    # so we detect PDF by magic bytes or filename extension and fall back to image extraction.
    uploaded_file.seek(0)
    raw = uploaded_file.read()
    import io as _io
    import imghdr
    import binascii
    buf = _io.BytesIO(raw)

    # Debug info for troubleshooting mobile uploads (also write a small server-side log)
    try:
        meta = f"Uploaded: {getattr(uploaded_file, 'name', '<unknown>')} | type: {getattr(uploaded_file, 'type', '<none>')} | size: {len(raw)} bytes"
        st.sidebar.write(meta)
        st.sidebar.write('First bytes: ' + binascii.hexlify(raw[:16]).decode(errors='ignore'))
        # append to debug log
        try:
            logp = Path(__file__).resolve().parent / 'tmp'
            logp.mkdir(exist_ok=True)
            with open(logp / 'upload_debug.log', 'a', encoding='utf-8') as lf:
                lf.write(meta + '\n')
                lf.write('first_bytes:' + binascii.hexlify(raw[:32]).decode() + '\n')
        except Exception:
            pass
    except Exception:
        pass

    # Detect pdf by magic bytes, filename, or MIME type
    is_pdf = False
    if (len(raw) >= 4 and raw[:4] == b'%PDF') or (hasattr(uploaded_file, 'type') and getattr(uploaded_file, 'type') == 'application/pdf') or (hasattr(uploaded_file, 'name') and getattr(uploaded_file, 'name').lower().endswith('.pdf')):
        is_pdf = True

    # Detect common image formats
    img_format = None
    try:
        img_format = imghdr.what(None, h=raw)
    except Exception:
        img_format = None

    # Detect HEIC/HEIF by ftyp box
    heic = False
    try:
        if b'ftypheic' in raw[:64] or b'ftypheix' in raw[:64] or b'ftyphevc' in raw[:64] or b'ftypmif1' in raw[:64]:
            heic = True
    except Exception:
        heic = False

    # If mobile returned HEIC, try to convert if pillow_heif is available
    if heic:
        try:
            import pillow_heif
            pillow_heif.register_heif_opener()
            buf.seek(0)
            from PIL import Image
            img = Image.open(buf).convert('RGB')
            out = _io.BytesIO()
            img.save(out, format='JPEG')
            raw = out.getvalue()
            buf = _io.BytesIO(raw)
            img_format = 'jpeg'
            st.sidebar.info('HEIC image converted to JPEG on server (pillow_heif available).')
        except Exception:
            st.sidebar.warning('HEIC image detected. If extraction fails, convert the image to JPG/PNG on your phone before uploading.')

    # If file size looks very large, warn the user (common on mobile photos)
    if len(raw) > 10 * 1024 * 1024:
        st.sidebar.warning('Uploaded file is large (>10MB). Mobile uploads can fail if the host blocks large files. Consider compressing.')

    # Extraction
    if is_pdf:
        try:
            buf.seek(0)
            text = extract_text_from_pdf(buf)
        except Exception as e:
            try:
                text = extract_text_from_pdf(_io.BytesIO(raw))
            except Exception as e2:
                st.error('Failed to extract text from PDF: ' + str(e2))
                text = ''
    else:
        # If imghdr couldn't detect format but filename indicates image, still try
        if img_format is None and (hasattr(uploaded_file, 'name') and getattr(uploaded_file, 'name').lower().endswith(('.png', '.jpg', '.jpeg'))):
            img_format = 'jpeg'
        if img_format is None and not heic:
            st.sidebar.info('Uploaded file does not look like a standard image (imghdr unknown). We will still try image OCR.')
        try:
            buf.seek(0)
            text = extract_text_from_image(buf)
        except Exception as e:
            try:
                text = extract_text_from_image(_io.BytesIO(raw))
            except Exception as e2:
                st.error('Failed to extract text from image: ' + str(e2))
                text = ''

    # Provide a paste-text fallback for mobile users
    if not text.strip():
        pasted = st.sidebar.text_area('Or paste resume text here (mobile fallback)', value='')
        if pasted and not text:
            text = pasted
    st.subheader('Extracted text')
    st.text_area('Resume text', value=text, height=300)

    # clean + predict
    cleaned = clean_text(text)
    if not predictor.ready:
        st.warning('No trained model artifacts found. Train model or upload artifacts.zip in the sidebar.')
    else:
        pred, score = predictor.predict_text(cleaned)
        st.subheader('Prediction')
        st.write(f'Match prediction: **{pred}**')
        if score is not None:
            st.write(f'Confidence / score: **{score:.3f}**')
        # suggestions: short or deep (long-form)
        # default to deep suggestions on so users see full paragraphs by default
        deep = st.checkbox('Deep suggestions (long, tailored)', value=True)
        if deep:
            deep_sugs = generate_deep_suggestions(text)
            if deep_sugs:
                st.subheader('Deep suggestions (tailored)')
                for p in deep_sugs:
                    # render as markdown to preserve paragraph breaks and formatting
                    st.markdown(p.replace('\n', '\n\n'))
                    st.markdown('---')
        else:
            suggestions = generate_suggestions(text)
            if suggestions:
                st.subheader('Suggestions to improve this resume')
                for s in suggestions:
                    st.write('- ' + s)

st.markdown('---')
st.info('To train a model, run `models/train.py` locally and copy the artifacts to `./artifacts` or upload an artifacts zip in the sidebar.')