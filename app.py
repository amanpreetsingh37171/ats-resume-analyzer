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
        from models.predict import Predictor
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

if uploaded_file is not None and st.sidebar.button('Extract & Predict'):
    # extract text
    text = ''
    if uploaded_file.type == 'application/pdf':
        text = extract_text_from_pdf(uploaded_file)
    else:
        text = extract_text_from_image(uploaded_file)
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