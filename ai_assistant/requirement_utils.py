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


REQUIREMENT_MARKERS = [
    "anforderungen",
    "ihr profil",
    "profil",
    "kenntnisse",
    "erfahrung",
    "qualifikation",
    "sicherer umgang",
    "wünschenswert",
    "erforderlich",
    "voraussetzung",
    "skills",
    "requirements",
    "experience",
    "qualification",
    "profile",
]


def normalize_text(text):
    return re.sub(r"\s+", " ", text or "").strip().lower()


def extract_keywords(text, max_keywords=80):
    """
    Generic keyword extractor.

    No fixed industry skill list.
    Works for software, engineering, construction, finance, healthcare, etc.
    """

    words = re.findall(
        r"[A-Za-zÄÖÜäöüß0-9+#./-]{3,}",
        text or "",
    )

    cleaned_words = []

    for word in words:
        normalized = word.strip(".,;:()[]{}<>").lower()

        if not normalized:
            continue

        if normalized in STOP_WORDS:
            continue

        if normalized.isdigit():
            continue

        cleaned_words.append(normalized)

    counts = Counter(cleaned_words)

    return [
        word
        for word, _count in counts.most_common(max_keywords)
    ]


def extract_requirement_phrases(job_description, max_phrases=12):
    """
    Pull likely requirement/profile sentences from a job description.
    """

    text = job_description or ""

    sentence_candidates = re.split(
        r"(?<=[.!?])\s+|\n+",
        text,
    )

    requirement_phrases = []

    for sentence in sentence_candidates:
        clean_sentence = re.sub(r"\s+", " ", sentence).strip()

        if not clean_sentence:
            continue

        lowered = clean_sentence.lower()

        if any(marker in lowered for marker in REQUIREMENT_MARKERS):
            requirement_phrases.append(clean_sentence)

    return requirement_phrases[:max_phrases]


def build_job_requirement_profile(job_description):
    """
    Build a neutral requirement profile from the job description.
    """

    return {
        "keywords": extract_keywords(job_description),
        "requirement_phrases": extract_requirement_phrases(job_description),
    }


def compare_keyword_overlap(candidate_text, job_description):
    """
    First-pass generic comparison between candidate material and job text.

    Later this can be replaced or supplemented with AI/semantic matching.
    """

    candidate_keywords = set(extract_keywords(candidate_text))
    job_keywords = set(extract_keywords(job_description))

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
        "requirement_phrases": extract_requirement_phrases(job_description),
    }
