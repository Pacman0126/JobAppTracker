import re
from collections import Counter


STOP_WORDS = {
    # German
    "und", "oder", "der", "die", "das", "den", "dem", "des",
    "ein", "eine", "einer", "einem", "einen", "mit", "für",
    "von", "im", "in", "auf", "als", "sie", "wir", "ihre",
    "ihr", "unser", "unsere", "bei", "aus", "zum", "zur",
    "sowie", "auch", "durch", "nach", "über", "unter",
    "werden", "wird", "sind", "ist", "haben", "hat",

    # English
    "the", "and", "with", "for", "from", "you", "our", "your",
    "are", "is", "have", "has", "will", "this", "that", "into",
}


LANGUAGE_SYNONYMS = {
    "deutsch": "german",
    "deutschkenntnisse": "german",
    "german": "german",
    "englisch": "english",
    "englischkenntnisse": "english",
    "english": "english",
}


GENERIC_NOISE = {
    "lebenslauf",
    "resume",
    "cv",
    "logo",
    "slide",
    "number",
    "user",
    "passt",
    "hervorragend",
    "geschätzt",
    "vollzeit",
    "teilzeit",
    "festanstellung",
    "anstellung",
    "erschienen",
    "woche",
    "jahr",
    "gmbh",
    "ag",
    "kg",
    "inc",
    "ltd",
    "llc",
}


def normalize_text(text):
    return re.sub(r"\s+", " ", text or "").strip().lower()


def tokenize(text):
    return re.findall(
        r"[A-Za-zÄÖÜäöüß0-9+#./-]{3,}",
        text or "",
    )


def normalize_keyword(word):
    normalized = word.strip(".,;:()[]{}<>").lower()

    if not normalized:
        return ""

    normalized = LANGUAGE_SYNONYMS.get(normalized, normalized)

    return normalized


def extract_identity_noise(text, max_lines=6):
    """
    Dynamically remove personal/contact/header noise from a CV.

    This avoids hardcoding names like Oliver/Hartmann while still removing
    whatever name, email, phone, GitHub handle, or document title appears
    in the first lines of a CV.
    """
    lines = [
        line.strip()
        for line in (text or "").splitlines()
        if line.strip()
    ]

    header_text = " ".join(lines[:max_lines])
    noise = set()

    for token in tokenize(header_text):
        keyword = normalize_keyword(token)

        if not keyword:
            continue

        if "@" in keyword:
            noise.add(keyword)
            continue

        if "." in keyword and not keyword in {"c#", "c++", "vb.net"}:
            noise.add(keyword)
            continue

        if any(char.isdigit() for char in keyword):
            noise.add(keyword)
            continue

        noise.add(keyword)

    return noise


def extract_keywords(text, max_keywords=80, extra_noise=None):
    extra_noise = extra_noise or set()
    cleaned_words = []

    for word in tokenize(text):
        normalized = normalize_keyword(word)

        if not normalized:
            continue

        if normalized in STOP_WORDS:
            continue

        if normalized in GENERIC_NOISE:
            continue

        if normalized in extra_noise:
            continue

        if normalized.isdigit():
            continue

        if any(char.isdigit() for char in normalized):
            continue

        if normalized.startswith("/"):
            continue

        if ".pdf" in normalized:
            continue

        if len(normalized) < 3:
            continue

        cleaned_words.append(normalized)

    counts = Counter(cleaned_words)

    return [
        word
        for word, _count in counts.most_common(max_keywords)
    ]


def compare_candidate_to_job(candidate_text, job_text):

    candidate_identity_noise = extract_identity_noise(candidate_text)

    shared_noise = candidate_identity_noise

    candidate_keywords = set(
        extract_keywords(
            candidate_text,
            extra_noise=shared_noise,
        )
    )

    job_keywords = set(
        extract_keywords(
            job_text,
            extra_noise=shared_noise,
        )
    )

    matched_keywords = sorted(candidate_keywords & job_keywords)
    missing_keywords = sorted(job_keywords - candidate_keywords)

    if not job_keywords:
        match_score = 0
    else:
        match_score = round(
            len(matched_keywords) / len(job_keywords) * 100
        )

    return {
        "match_score": match_score,
        "matched_keywords": matched_keywords[:40],
        "missing_keywords": missing_keywords[:40],
        "candidate_keywords": sorted(candidate_keywords)[:80],
        "job_keywords": sorted(job_keywords)[:80],
    }


def build_candidate_recommendation(analysis):
    score = analysis.get("match_score", 0)
    matched = analysis.get("matched_keywords", [])
    missing = analysis.get("missing_keywords", [])

    if score >= 70:
        summary = "Strong candidate fit based on keyword overlap."
    elif score >= 40:
        summary = "Partial candidate fit. The application should emphasize transferable experience."
    else:
        summary = "Limited direct keyword overlap. The application should emphasize transferable experience."

    strengths = matched[:10]
    gaps = missing[:10]

    recommendations = []

    if strengths:
        recommendations.append(
            "Emphasize the strongest overlapping skills and experience."
        )

    if gaps:
        recommendations.append(
            "Address important missing or weakly represented requirements honestly."
        )

    recommendations.append(
        "Do not invent experience. Use transferable skills where direct matches are limited."
    )

    return {
        "summary": summary,
        "strengths": strengths,
        "gaps": gaps,
        "recommendations": recommendations,
    }


def analyze_candidate_fit(candidate_text, job_text):
    analysis = compare_candidate_to_job(
        candidate_text=candidate_text,
        job_text=job_text,
    )

    recommendation = build_candidate_recommendation(analysis)

    return {
        **analysis,
        "summary": recommendation["summary"],
        "strengths": recommendation["strengths"],
        "gaps": recommendation["gaps"],
        "recommendations": recommendation["recommendations"],
    }
