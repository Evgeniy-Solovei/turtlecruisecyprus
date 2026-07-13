from __future__ import annotations

import re
from pathlib import Path

from django.conf import settings

from .i18n import DEFAULT_LOCALE, public_page_url

# Fallback copy when CMS import is missing (matches live WP where noted).
HOME_COPY: dict[str, dict[str, str]] = {
    "en": {
        "hero_title": "Some things you just <em>have to see</em>",
        "hero_sub": "Morning or sunset. Scenic views. Small adventure, big memory.",
        "choose_cruise": "Choose your cruise",
        "morning_tour_title": "<em>Morning</em> Cruise",
        "morning_tour_time": "9:30 – 14:00",
        "morning_tour_desc": "The best time to spot turtles.",
        "sunset_tour_title": "<em>Sunset</em> Cruise",
        "sunset_tour_time": "16:00 – 20:00",
        "sunset_tour_desc": "Cruise vibe in golden light",
    },
    "de": {
        "hero_title": "Manche Dinge muss man einfach selbst gesehen haben",
        "hero_sub": (
            "Morgens oder zum Sonnenuntergang. Schildkröten? So gut wie garantiert. "
            "Kleines Abenteuer, große Erinnerung."
        ),
        "choose_cruise": "Wähl deine Tour",
        "morning_tour_title": "Morgentour",
        "morning_tour_time": "9:30 – 14:00 Uhr",
        "morning_tour_desc": "Die beste Zeit, um Schildkröten zu sehen.",
        "sunset_tour_title": "Sunset-Cruise",
        "sunset_tour_time": "16:00 – 20:00 Uhr",
        "sunset_tour_desc": "Kreuzfahrt-Atmosphäre im goldenen Licht",
    },
}

# Prod hero assets (WP uploads). sync_wp_media copies these into media/wp/.
HERO_MEDIA: dict[str, str] = {
    "bg_desktop": "2026/06/img-9303.webp",
    "bg_mobile": "2026/06/img-9303.webp",
    "morning_tour": "2026/06/img-0342-scaled-e1780686880446-300x250.webp",
    "sunset_tour": "2026/06/img-7239-scaled-e1780686923559-262x300.webp",
}

HERO_STATIC_FALLBACK: dict[str, str] = {
    "bg_desktop": "frontend/img/dist/hero-bg.jpg",
    "bg_mobile": "frontend/img/dist/hero-bg.jpg",
    "morning_tour": "frontend/img/dist/morning-cruise.jpg",
    "sunset_tour": "frontend/img/dist/sunset-cruise.jpg",
}

BENEFIT_MEDIA = [
    {
        "wp": "2026/06/img-7434-scaled-e1780688241237.webp",
        "static": "frontend/img/dist/benefit-1.jpg",
        "alt_en": "A Catamaran",
        "alt_de": "Ein Katamaran",
    },
    {
        "wp": "2026/06/img-3925-e1780690399980.webp",
        "static": "frontend/img/dist/benefit-2.jpg",
        "alt_en": "Made this morning",
        "alt_de": "Heute Morgen zubereitet",
    },
    {
        "wp": "2026/05/benefit-3.webp",
        "static": "frontend/img/dist/benefit-3.jpg",
        "alt_en": "Captain Jimmy",
        "alt_de": "Kapitän Jimmy",
    },
]

BENEFITS_COPY: dict[str, dict] = {
    "en": {
        "header_title": "What Makes Us <em>Different</em>",
        "header_sub": "Family-owned. Freshly cooked. Truly personal.",
        "items": [
            {
                "title": "<em>A Catamaran.</em> Not Just a Yacht",
                "lead": "Two decks. Maximum comfort on the water",
                "body": (
                    "The perfect boat design for getting close to sea caves, watching turtles, "
                    "and taking photos with a beautiful view. You will definitely feel the "
                    "difference as soon as you get on board."
                ),
                "video_url": "https://youtube.com/shorts/bGox7T5de08",
                "button_label": "WATCH NOW",
            },
            {
                "title": "<em>Made this morning.</em> Real food.",
                "lead": "Traditional Cypriot taste and quality.",
                "body": (
                    "Every dish is cooked fresh from home recipes before we leave the harbour. "
                    "Grilled chicken and halloumi – done right on deck, while you sail. "
                    "Nobody else in Ayia Napa does this. Nobody."
                ),
                "video_url": "https://youtube.com/shorts/MGfyuvQ43Rs",
                "button_label": "HOW WE COOK",
            },
            {
                "title": "Captain <em>Jimmy</em>",
                "lead": "40 years of experience in sailing and diving",
                "body": (
                    'Built this boat from scratch. A family business – and you feel it the moment '
                    'you step on board. People come back to Cyprus and ask: "Is it the same captain '
                    'this year?" Yes. Always.'
                ),
            },
        ],
    },
    "de": {
        "header_title": "Was uns besonders <em>macht</em>",
        "header_sub": "Familienbetrieb. Frisch gekocht. Wirklich persönlich.",
        "items": [
            {
                "title": "<em>Ein Katamaran.</em> Keine gewöhnliche Yacht",
                "lead": "Zwei Decks. Maximaler Komfort auf dem Wasser",
                "body": (
                    "Das perfekt gebaute Boot, um nah an die Meereshöhlen heranzukommen, "
                    "Schildkröten zu beobachten und Fotos vor traumhafter Kulisse zu machen. "
                    "Den Unterschied spürst du, sobald du an Bord kommst."
                ),
                "video_url": "https://youtube.com/shorts/bGox7T5de08",
                "button_label": "Yacht ansehen",
            },
            {
                "title": "<em>Heute Morgen zubereitet.</em> Echtes Essen.",
                "lead": "Traditioneller zyprischer Geschmack und Qualität.",
                "body": (
                    "Jedes Gericht wird nach Familienrezepten frisch zubereitet, bevor wir den "
                    "Hafen verlassen. Gegrilltes Hähnchen und Halloumi – direkt an Deck, während "
                    "du übers Meer fährst. Sonst macht das niemand in Ayia Napa. Niemand."
                ),
                "video_url": "https://youtube.com/shorts/MGfyuvQ43Rs",
                "button_label": "WIE WIR KOCHEN",
            },
            {
                "title": "Kapitän <em>Jimmy</em>",
                "lead": "40 Jahre Erfahrung im Segeln und Tauchen",
                "body": (
                    "Er hat dieses Boot von Grund auf selbst gebaut. Ein Familienbetrieb – und das "
                    "spürst du in dem Moment, in dem du an Bord kommst. Gäste kommen nach Zypern "
                    "zurück und fragen: „Ist es dieses Jahr derselbe Kapitän?“ Ja. Immer."
                ),
            },
        ],
    },
}


def _media_url(wp_rel: str, static_fallback: str) -> dict[str, str]:
    rel = wp_rel.lstrip("/")
    if rel.startswith("media/wp/"):
        rel = rel[len("media/wp/") :]
    disk = Path(settings.MEDIA_ROOT) / "wp" / rel
    if disk.is_file():
        return {"url": f"/media/wp/{rel}", "kind": "media"}
    return {"url": static_fallback, "kind": "static"}


def _youtube_embed(url: str) -> str:
    value = (url or "").strip()
    if not value or "youtube-nocookie.com/embed/" in value:
        return value
    match = re.search(r"(?:shorts/|v=|embed/|youtu\.be/)([\w-]{11})", value)
    if not match:
        return value
    return f"https://www.youtube-nocookie.com/embed/{match.group(1)}?rel=0"


def benefits_context(locale: str) -> dict:
    loc = locale if locale in BENEFITS_COPY else DEFAULT_LOCALE
    data = BENEFITS_COPY[loc]
    items = []
    for idx, item in enumerate(data["items"]):
        media_cfg = BENEFIT_MEDIA[idx]
        image = _media_url(media_cfg["wp"], media_cfg["static"])
        image["alt"] = media_cfg[f"alt_{loc}"]
        row = {**item, "image": image}
        if row.get("video_url"):
            row["video_url"] = _youtube_embed(row["video_url"])
        items.append(row)
    return {
        "header_title": data["header_title"],
        "header_sub": data["header_sub"],
        "items": items,
    }


def home_context(locale: str) -> dict:
    loc = locale if locale in HOME_COPY else DEFAULT_LOCALE
    copy = HOME_COPY[loc]
    media = {key: _media_url(HERO_MEDIA[key], HERO_STATIC_FALLBACK[key]) for key in HERO_MEDIA}
    return {
        "copy": copy,
        "media": media,
        "morning_tour_url": public_page_url(loc, "/chill-cruise/"),
        "sunset_tour_url": public_page_url(loc, "/sunset-cruise/"),
    }
