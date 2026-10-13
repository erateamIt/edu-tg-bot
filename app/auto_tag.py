"""Automatic customer tagging based on keyword heuristics."""
import re

from app import database as db
from app.core import config

DEFAULT_TAGS = {
    "python": {"name": "🐍 Python", "description": "Python course interest"},
    "backend": {"name": "💻 Backend", "description": "Backend development interest"},
    "frontend": {"name": "🌐 Frontend", "description": "Frontend development interest"},
    "ielts": {"name": "🇬🇧 IELTS", "description": "IELTS course interest"},
    "english": {"name": "📚 English", "description": "English course interest"},
    "price": {"name": "💰 Price", "description": "Pricing questions"},
    "location": {"name": "📍 Location", "description": "Location questions"},
    "course_date": {"name": "📅 Course Date", "description": "Course start date questions"},
    "interested": {"name": "🔥 Interested", "description": "Customer expresses interest"},
    "registered": {"name": "🟢 Registered", "description": "Customer already registered"},
    "not_interested": {"name": "🔴 Not Interested", "description": "Customer not interested"},
    "general": {"name": "❓ General Question", "description": "General question"},
}

KEYWORD_MAP = {
    "python": ["python", "python kurs", "python dasturlash", "backend python"],
    "backend": ["backend", "server", "api", "django", "fastapi"],
    "frontend": ["frontend", "front end", "react", "javascript", "html", "css"],
    "ielts": ["ielts", "speaking", "writing", "listening", "reading"],
    "english": ["ingliz tili", "english", "inglizcha"],
    "price": ["narx", "qancha", "to'lov", "tolov", "pul", "summa", "chegirma"],
    "location": ["manzil", "qayerda", "adres", "address", "lokatsiya"],
    "course_date": ["qachon", "boshlanadi", "boshlanish", "sana", "vaqt", "dars qachon"],
    "interested": [
        "yozilmoqchiman",
        "yozilaman",
        "qatnashmoqchiman",
        "kursga kiraman",
        "ro'yxatdan o'taman",
        "ro'yxatdan otaman",
    ],
    "registered": ["ro'yxatdan o'tdim", "yozildim", "to'lov qildim", "tolov qildim"],
    "not_interested": ["kerak emas", "qiziq emas", "bormayman", "qatnashmayman"],
}

AUTO_STATUS_MAP = {
    "interested": "interested",
    "registered": "registered",
    "not_interested": "not_interested",
}


def normalize_text(value):
    if value is None:
        return ""
    text = str(value).strip().lower()
    replacements = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201b": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u02bb": "'",
        "\u02bc": "'",
        "’": "'",
        "‘": "'",
        "ʻ": "'",
        "o‘": "o'",
        "o’": "o'",
        "oʻ": "o'",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _match_confidence(message, keyword):
    keyword_norm = normalize_text(keyword)
    if not keyword_norm:
        return 0.0
    if keyword_norm == message:
        return 1.0
    if keyword_norm in message:
        return 1.0 if len(keyword_norm) >= 3 else 0.8
    return 0.0


def classify_message(text):
    normalized = normalize_text(text)
    if not normalized:
        return []
    matches = []
    for slug, keywords in KEYWORD_MAP.items():
        best = 0.0
        for keyword in keywords:
            confidence = _match_confidence(normalized, keyword)
            if confidence > best:
                best = confidence
        if best >= 0.8:
            matches.append({
                "slug": slug,
                "name": DEFAULT_TAGS[slug]["name"],
                "source": "keyword",
                "confidence": round(best, 2),
            })
    return matches


def _optional_ai_classify(text):
    enabled = str(getattr(config, "AUTO_TAG_AI_ENABLED", False)).lower() == "true"
    if not enabled:
        return []
    return []


def ensure_default_tags():
    for slug, meta in DEFAULT_TAGS.items():
        db.ensure_tag(meta["name"], slug=slug, description=meta["description"])


def apply_auto_tags_for_customer(customer_id, text, threshold=None):
    if customer_id is None:
        return []
    enabled = str(db.get_setting("auto_tag_enabled", "true") or "true").lower() == "true"
    if not enabled:
        return []
    normalized = normalize_text(text)
    if not normalized:
        return []
    threshold_value = threshold
    if threshold is None:
        threshold_value = float(
            db.get_setting("auto_tag_min_confidence", str(getattr(config, "AUTO_TAG_MIN_CONFIDENCE", 0.70))) or 0.70
        )
    matches = classify_message(normalized)
    if not matches:
        matches = _optional_ai_classify(normalized)
    result = []
    for match in matches:
        if match["confidence"] < threshold_value:
            continue
        db.add_customer_tag(
            customer_id,
            match["name"],
            source=match["source"],
            confidence=match["confidence"],
            slug=match["slug"],
        )
        status = AUTO_STATUS_MAP.get(match["slug"])
        if status:
            customer = db.get_customer_by_id(customer_id)
            if customer and customer.get("status_source") in (None, "automatic"):
                db.set_customer_status(customer_id, status, status_source="automatic")
        result.append(match)
    return result


def auto_tag_customer(customer_id, text):
    return apply_auto_tags_for_customer(customer_id, text)
