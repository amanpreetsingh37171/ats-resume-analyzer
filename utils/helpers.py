import re
def extract_skills_from_text(text, delimiter_regex=r'[;,\n]'):
    parts = [p.strip() for p in re.split(delimiter_regex, text.lower()) if p.strip()]
    return parts
