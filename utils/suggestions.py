import re
from pathlib import Path
from .helpers import extract_skills_from_text

def _has_email(text):
    return bool(re.search(r"\b[\w.%+-]+@[\w.-]+\.[A-Za-z]{2,}\b", text))

def _has_phone(text):
    return bool(re.search(r"\b(\+?\d[\d\s\-()]{6,}\d)\b", text))

def _word_count(text):
    return len(text.split()) if isinstance(text, str) else 0

def _has_numbers(text):
    return bool(re.search(r"\d", text))


def generate_suggestions(text: str, max_suggestions: int = 6):
    """Return a list of suggestion strings for the given resume text.

    The rules are simple and heuristic-based:
    - Recommend adding contact details if missing.
    - Recommend expanding a too-short summary/objective.
    - Recommend shortening very long resumes.
    - Suggest listing more skills when few detected.
    - Recommend adding bullets or sections if content looks like a paragraph.
    - Recommend quantifying achievements if no numbers are present.
    """
    if not isinstance(text, str) or not text.strip():
        return [
            "Resume text is empty — add a brief summary, contact info, and key skills.",
        ]

    suggestions = []
    wc = _word_count(text)

    # Contact info
    if not _has_email(text):
        suggestions.append("Add an email address at the top so recruiters can contact you.")
    if not _has_phone(text):
        suggestions.append("Add a phone number or other contact method (phone/LinkedIn).")

    # Summary / objective
    if wc < 50:
        suggestions.append("The resume is very short — expand the summary/objective with 2-3 lines about your experience and goals.")
    elif wc > 2000:
        suggestions.append("The resume looks long — condense to 1-2 pages and keep only most relevant experience.")

    # Skills
    skills = extract_skills_from_text(text)
    if len(skills) < 3:
        suggestions.append("List 5–10 concrete technical or domain skills (e.g., Python, SQL, Project Management).")

    # Bullets / readability
    # Count newlines and sentences approximated by periods
    newlines = text.count('\n')
    sentences = text.count('.')
    if newlines < 3 and sentences > 3:
        suggestions.append("Use bullet points for responsibilities and achievements rather than long paragraphs for readability.")

    # Quantify achievements
    if not _has_numbers(text):
        suggestions.append("Where possible, quantify achievements (e.g., 'Improved X by 30%') to show impact.")

    # Formatting / grammar hints (basic)
    # If too many uppercase words (possible ALL CAPS sections)
    uppercase_words = sum(1 for w in re.findall(r"\b[A-Z]{2,}\b", text))
    if uppercase_words > 10:
        suggestions.append("Avoid ALL-CAPS sections; use normal sentence case for readability.")

    # Deduplicate and limit
    seen = set()
    final = []
    for s in suggestions:
        if s not in seen:
            final.append(s)
            seen.add(s)
        if len(final) >= max_suggestions:
            break

    return final


def generate_deep_suggestions(text: str, max_paragraphs: int = 6):
    """Generate longer, resume-specific suggestions (paragraphs) tailored to the resume text.

    Each suggestion is a multi-sentence paragraph explaining what to improve and how,
    plus concrete examples or templates where applicable. This function uses heuristic
    rules and simple templates; it does not call external APIs.
    """
    if not isinstance(text, str) or not text.strip():
        return [
            (
                "Resume is empty — add a concise professional summary at the top, include contact "
                "information (email, phone, LinkedIn), and list 5–10 core technical or domain skills. "
                "Aim for 200–400 words across the resume for an early-career candidate, and 400–800 "
                "for more experienced profiles."
            )
        ]

    paragraphs = []

    def has_email(t):
        return bool(re.search(r"\b[\w.%+-]+@[\w.-]+\.[A-Za-z]{2,}\b", t))

    def has_phone(t):
        return bool(re.search(r"\b(\+?\d[\d\s\-()]{6,}\d)\b", t))

    def extract_head(text):
        # first few lines, used to show current top-of-resume content
        head_lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
        if head_lines:
            return ' '.join(head_lines[:3])[:600]
        return text[:600]

    # 1) Contact & header
    if not has_email(text) or not has_phone(text):
        paragraphs.append(
            (
                "Contact and header: Your resume should start with a clear header containing your full name, "
                "professional title (optional), email address, phone number, and a LinkedIn or personal site link if available. "
                "Recruiters often screen by contact details first — include an email and phone at the very top. "
                "Example header: 'Jane Doe — Data Engineer | jane.doe@example.com | +1 555-123-4567 | linkedin.com/in/janedoe'."
            )
        )

    # 2) Summary / Objective rewrite with sample
    summary = extract_head(text)
    skills = extract_skills_from_text(text)
    top_skills = [s.title() for s in skills[:6]]
    skill_phrase = ', '.join(top_skills) if top_skills else ''
    suggested_summary = (
        (f"Experienced {skill_phrase} professional" if skill_phrase else "Experienced professional")
        + ", with a proven track record of delivering measurable results in cross-functional teams. "
        + "Skilled at translating business needs into data-driven solutions and delivering reliable production-ready systems. "
        + "Target roles: data engineering, analytics, or machine learning engineering."
    )
    paragraphs.append(
        (
            "Summary / Objective: Your opening paragraph should be 2–4 sentences that clearly state who you are, "
            "your main technical strengths, and the role you seek. Current detected top lines: '" + (summary[:260].replace('\n',' ') + "'...")
            + "\n\nSuggested summary example: '" + suggested_summary + "'"
        )
    )

    # 3) Skills section guidance
    paragraphs.append(
        (
            "Skills & Keywords: Add a dedicated 'Skills' section with 6–15 concrete keywords grouped by type (Programming, Tools, Data, Cloud). "
            "Place the most relevant skills first and include synonyms (e.g., 'AWS' and 'Amazon Web Services'). "
            + ("Example skills to add: " + skill_phrase + "." if skill_phrase else "Example skills: Python, SQL, Docker, AWS, Spark.")
        )
    )

    # 4) Experience -> achievements and quantification
    paragraphs.append(
        (
            "Experience & achievements: Replace vague responsibility statements with concise achievement bullets that quantify impact. "
            "Start bullets with action verbs and add metrics where possible (e.g., 'Reduced API latency by 35%', 'Cut data processing costs by $50k/year'). "
            "If you cannot disclose exact numbers, use approximate ranges or percentages."
        )
    )

    # 5) Formatting & ATS
    paragraphs.append(
        (
            "Formatting & ATS optimization: Use a simple single-column layout, standard headings, and avoid images or complex tables. "
            "Include role-specific keywords from job postings in the 'Skills' and 'Experience' sections. Save as a clean PDF when applying through company portals."
        )
    )

    # 6) Education / Projects / Certifications
    paragraphs.append(
        (
            "Education & Projects: For each project or role, include a one-line context, one-line technical approach, and one-line outcome/metric. "
            "List certifications with issuer and date. For project-driven applicants, a 'Selected Projects' section helps showcase hands-on experience."
        )
    )

    # Optional: provide a concrete rewrite for a short sentence
    sentences = re.split(r'[\n\.]\s*', text)
    short_sent = None
    for s in sentences:
        s = s.strip()
        if 8 < len(s.split()) < 25:
            short_sent = s
            break
    if short_sent:
        example = (
            "Example rewrite: Transform a generic responsibility into a quantified achievement.\n"
            f"Original: '{short_sent}'\n"
            "Suggested: '" + short_sent.split(':')[-1].strip().capitalize() + " — achieved measurable improvements by implementing X, resulting in Y% improvement.'"
        )
        paragraphs.append(example)

    return paragraphs[:max_paragraphs]
