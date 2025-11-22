# Training script for ATS Resume Analyzer
import pandas as pd
import joblib
import argparse
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
from utils.clean import clean_text
from pathlib import Path
import os
import json

def train(csv_path, text_column, label_column, artifacts_dir='./artifacts'):
    df = pd.read_csv(csv_path)
    df = df[[text_column, label_column]].dropna()
    X = df[text_column].astype(str).apply(clean_text)
    y = df[label_column]
    # If the label is continuous (e.g., a score), convert to binary classes (threshold 0.5)
    try:
        from pandas.api.types import is_numeric_dtype
        if is_numeric_dtype(y.dtype):
            # if many unique continuous values, binarize
            if y.nunique() > 2:
                y = (y.astype(float) > 0.5).astype(int)
    except Exception:
        pass
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    vectorizer = TfidfVectorizer(max_features=20000, ngram_range=(1,2))
    X_train_tfidf = vectorizer.fit_transform(X_train)
    X_test_tfidf = vectorizer.transform(X_test)
    model = LogisticRegression(max_iter=1000)
    model.fit(X_train_tfidf, y_train)
    preds = model.predict(X_test_tfidf)
    acc = accuracy_score(y_test, preds)
    print('Accuracy:', acc)
    print('Classification report:\n', classification_report(y_test, preds))
    p = Path(artifacts_dir); p.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, p / 'model.joblib')
    joblib.dump(vectorizer, p / 'vectorizer.joblib')
    # save metadata
    meta = {'text_column': text_column, 'label_column': label_column}
    with open(p / 'meta.json', 'w') as f:
        json.dump(meta, f)
    print('Artifacts saved to', str(p))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    # default to the repo-level `resume_data.csv` so script can be run from IDE/terminal easily
    parser.add_argument('--csv', default=str(Path(__file__).resolve().parents[1] / 'resume_data.csv'))
    parser.add_argument('--text-col', default='resume_text')
    parser.add_argument('--label-col', default='label')
    parser.add_argument('--out', default='./artifacts')
    args = parser.parse_args()
    train(args.csv, args.text_col, args.label_col, args.out)