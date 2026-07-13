from __future__ import annotations

SUPPORTED_LOCALES = ("en", "de")
DEFAULT_LOCALE = "en"

# WP Polylang slug → Django route path (without locale prefix)
DE_URL_ALIASES = {
    "morgenrundfahrt": "chill-cruise/",
    "sonnenuntergangstour": "sunset-cruise/",
    "galerie": "gallery/",
    "bewertungen": "reviews/",
    "haeufige-fragen": "faq/",
    "kontakt-ueber-uns": "contacts/",
    "vielen-dank-fuer-ihre-buchung": "thank-you/",
    "privatcharter": "private-charter/",
    "datenschutz": "privacy-policy/",
    "agb": "terms-conditions/",
}

DE_SLUG_MAP = {
    "de": "",
    "morgenrundfahrt": "chill-cruise/",
    "sonnenuntergangstour": "sunset-cruise/",
    "private-charter": "private-charter/",
    "galerie": "gallery/",
    "bewertungen": "reviews/",
    "haeufige-fragen": "faq/",
    "blog": "blog/",
    "kontakt-ueber-uns": "contacts/",
    "vielen-dank-fuer-ihre-buchung": "thank-you/",
}

EN_SLUG_MAP = {
    "home": "",
    "cruise": "chill-cruise/",
    "chill-cruise": "chill-cruise/",
    "sunset-cruise": "sunset-cruise/",
    "private-charter": "private-charter/",
    "gallery": "gallery/",
    "reviews": "reviews/",
    "faq": "faq/",
    "blog": "blog/",
    "about": "about/",
    "contacts": "contacts/",
    "contacts-about": "contacts/",
    "thank-you": "thank-you/",
    "privacy-policy": "privacy-policy/",
    "terms-conditions": "terms-conditions/",
    "terms": "terms-conditions/",
    "fulfillment-policy": "fulfillment-policy/",
}

REVERSE_DE_ALIASES = {path.rstrip("/"): alias for alias, path in DE_URL_ALIASES.items()}


def _strip_locale_prefix(path: str) -> str:
    path = path if path.startswith("/") else f"/{path}"
    if path == "/":
        return ""
    return path.strip("/")


def _canonical_slug(path: str) -> str:
    slug = _strip_locale_prefix(path)
    if slug.startswith("de/"):
        slug = slug[3:]
    if slug.startswith("blog/"):
        slug = slug[5:]
    slug = slug.rstrip("/")
    if slug in DE_URL_ALIASES:
        return DE_URL_ALIASES[slug].rstrip("/")
    return EN_SLUG_MAP.get(slug, slug)


def language_switch_url(from_locale: str, to_locale: str, current_path: str) -> str:
    canon = _canonical_slug(current_path)
    blog_slug = ""
    stripped = _strip_locale_prefix(current_path).rstrip("/")
    if stripped.startswith("de/blog/"):
        blog_slug = stripped.split("/", 2)[-1]
    elif stripped.startswith("blog/"):
        blog_slug = stripped.split("/", 1)[-1]
    elif stripped:
        maybe_blog = _maybe_blog_slug(stripped)
        if maybe_blog:
            blog_slug = maybe_blog

    if blog_slug:
        if to_locale == DEFAULT_LOCALE:
            return f"/{blog_slug}/"
        return f"/de/{blog_slug}/"

    if to_locale == DEFAULT_LOCALE:
        en_path = EN_SLUG_MAP.get(canon, canon).rstrip("/")
        return localized_path(DEFAULT_LOCALE, f"/{en_path}/" if en_path else "/")

    de_alias = REVERSE_DE_ALIASES.get(canon)
    if de_alias:
        return f"/de/{de_alias}/"
    if canon:
        return f"/de/{canon}/"
    return "/de/"


def _maybe_blog_slug(path: str) -> str:
    from apps.cms.models import BlogPost

    slug = path.strip("/")
    if slug.startswith("de/"):
        slug = slug[3:]
    if "/" in slug:
        return ""
    if BlogPost.objects.filter(slug=slug, is_published=True).exists():
        return slug
    return ""


def language_links(current_locale: str, current_path: str) -> list[dict[str, str]]:
    links = []
    for code in SUPPORTED_LOCALES:
        if code == current_locale:
            continue
        links.append(
            {
                "slug": code,
                "url": language_switch_url(current_locale, code, current_path),
                "name": code.upper(),
            }
        )
    return links


BOOKING_I18N: dict[str, dict[str, str]] = {
    "en": {
        "popup_title": "Buy Turtle Cruise Ticket",
        "step_date": "date & time",
        "step_details": "your details",
        "step_payment": "payment",
        "time_remaining": "Time remaining:",
        "select_date": "Select Date",
        "select_cruise": "Select Cruise",
        "adults": "Adults",
        "children": "Children",
        "terms_title": "Terms and Conditions",
        "term_1": "Arrive at the port no later than 10 minutes before departure",
        "term_2": "No refunds will be made after payment",
        "term_3": "Date change allowed no later than 24 hours before the cruise",
        "term_4": "Bringing alcohol on board is prohibited",
        "term_5": "The route may be changed due to weather conditions",
        "term_6": "If the cruise is canceled — choose another date or full refund",
        "agree_terms": "I have read and agree to the Terms and Conditions",
        "agree_terms_required": "Please tick the box to confirm you have read and agree to the Terms and Conditions.",
        "enter_first_name": "Please enter your first name.",
        "enter_last_name": "Please enter your last name.",
        "enter_email": "Please enter your email address.",
        "invalid_email": "Please enter a valid email address (e.g. name@example.com).",
        "enter_phone": "Please enter your phone number.",
        "invalid_phone_generic": "Please enter a valid mobile number with country code (e.g. +357 97 123 456).",
        "invalid_phone_country": "Please choose the correct country code for your phone number.",
        "invalid_phone_too_short": "This phone number looks too short. Include the country code, e.g. +357 97 123 456.",
        "invalid_phone_too_long": "This phone number looks too long. Please check the digits you entered.",
        "invalid_phone_not_number": "Please enter digits only — start with + and your country code.",
        "select_hint": "Select a date and cruise to see details",
        "total": "Total:",
        "checkout": "Checkout",
        "first_name": "First name",
        "last_name": "Last name",
        "email": "Email",
        "phone": "Phone Number",
        "notes": "Additional notes",
        "optional": "optional",
        "required_fields": "Required fields.",
        "back": "Back",
        "loading_payment": "Loading payment form...",
        "book_now": "BOOK NOW",
        "menu": "Menu",
        "thank_you_title": "Thank you for your booking!",
        "thank_you_text": "Important: If you have not received your booking confirmation email within a few minutes, please check your Spam or Junk folder.",
        "close": "Close",
        "per_person": "per person",
        "required_marker": "*",
        "optional_hint": "(optional)",
        "place_order": "Place Order",
        "payment_success_title": "Thank you for your booking!",
        "payment_success_text": "Your payment has been successfully processed.",
        "payment_confirm_failed": "We could not verify your payment automatically. If you do not receive a confirmation email within a few minutes, please contact us and mention booking {booking_id}.",
        "aria_close": "Close",
        "aria_booking_dialog": "Book a Cruise",
        "adults_age": "(10+)",
        "children_age": "(2–10)",
        "book_section_title": "Book your cruise",
        "book_section_sub": "Ready to dive in?",
        "book_note": "Online booking only. Spots are limited. Free cancellation up to 24 hours before departure.\nBook early — prices increase as the boat fills up.",
        "processing": "Processing...",
        "blog_breadcrumb": "Blog",
    },
    "de": {
        "popup_title": "Turtle Cruise Ticket kaufen",
        "step_date": "Datum & Uhrzeit",
        "step_details": "Ihre Daten",
        "step_payment": "Zahlung",
        "time_remaining": "Verbleibende Zeit:",
        "select_date": "Datum wählen",
        "select_cruise": "Kreuzfahrt wählen",
        "adults": "Erwachsene",
        "children": "Kinder",
        "terms_title": "Allgemeine Geschäftsbedingungen",
        "term_1": "Bitte erscheinen Sie spätestens 10 Minuten vor Abfahrt am Hafen",
        "term_2": "Nach der Zahlung sind keine Rückerstattungen möglich",
        "term_3": "Datumänderung bis spätestens 24 Stunden vor der Kreuzfahrt möglich",
        "term_4": "Mitbringen von Alkohol an Bord ist verboten",
        "term_5": "Die Route kann aufgrund der Wetterbedingungen geändert werden",
        "term_6": "Bei Absage der Kreuzfahrt — anderes Datum wählen oder volle Rückerstattung",
        "agree_terms": "Ich habe die AGB gelesen und stimme zu",
        "agree_terms_required": "Bitte aktivieren Sie das Kontrollkästchen, um die AGB zu bestätigen.",
        "enter_first_name": "Bitte geben Sie Ihren Vornamen ein.",
        "enter_last_name": "Bitte geben Sie Ihren Nachnamen ein.",
        "enter_email": "Bitte geben Sie Ihre E-Mail-Adresse ein.",
        "invalid_email": "Bitte geben Sie eine gültige E-Mail-Adresse ein (z. B. name@beispiel.de).",
        "enter_phone": "Bitte geben Sie Ihre Telefonnummer ein.",
        "invalid_phone_generic": "Bitte geben Sie eine gültige Mobilnummer mit Ländercode ein (z. B. +357 97 123 456).",
        "invalid_phone_country": "Bitte wählen Sie den richtigen Ländercode für Ihre Telefonnummer.",
        "invalid_phone_too_short": "Die Telefonnummer ist zu kurz. Bitte mit Ländercode eingeben, z. B. +357 97 123 456.",
        "invalid_phone_too_long": "Die Telefonnummer ist zu lang. Bitte überprüfen Sie Ihre Eingabe.",
        "invalid_phone_not_number": "Bitte nur Ziffern eingeben — beginnen Sie mit + und Ihrem Ländercode.",
        "select_hint": "Wählen Sie Datum und Kreuzfahrt, um Details zu sehen",
        "total": "Gesamt:",
        "checkout": "Zur Kasse",
        "first_name": "Vorname",
        "last_name": "Nachname",
        "email": "E-Mail",
        "phone": "Telefonnummer",
        "notes": "Zusätzliche Anmerkungen",
        "optional": "optional",
        "required_fields": "Pflichtfelder.",
        "back": "Zurück",
        "loading_payment": "Zahlungsformular wird geladen...",
        "book_now": "JETZT BUCHEN",
        "menu": "Menü",
        "thank_you_title": "Vielen Dank für Ihre Buchung!",
        "thank_you_text": "Wichtig: Wenn Sie Ihre Buchungsbestätigung nicht innerhalb weniger Minuten erhalten haben, prüfen Sie bitte Ihren Spam- oder Junk-Ordner.",
        "close": "Schließen",
        "per_person": "pro Person",
        "required_marker": "*",
        "optional_hint": "(optional)",
        "place_order": "Bestellung aufgeben",
        "payment_success_title": "Vielen Dank für Ihre Buchung!",
        "payment_success_text": "Ihre Zahlung wurde erfolgreich verarbeitet.",
        "payment_confirm_failed": "Wir konnten Ihre Zahlung nicht automatisch bestätigen. Wenn Sie innerhalb weniger Minuten keine Bestätigungs-E-Mail erhalten, kontaktieren Sie uns bitte und nennen Sie die Buchungsnummer {booking_id}.",
        "aria_close": "Schließen",
        "aria_booking_dialog": "Kreuzfahrt buchen",
        "adults_age": "(10+)",
        "children_age": "(2–10)",
        "book_section_title": "Kreuzfahrt buchen",
        "book_section_sub": "Bereit einzutauchen?",
        "book_note": "Nur Online-Buchung. Plätze sind begrenzt. Kostenlose Stornierung bis 24 Stunden vor Abfahrt.\nFrüh buchen — die Preise steigen, wenn das Boot voller wird.",
        "related_articles": "Verwandte Artikel",
        "blog_breadcrumb": "Blog",
    },
}

SITE_I18N: dict[str, dict[str, str]] = {
    "en": {
        "nav_morning": "Morning Cruise",
        "nav_sunset": "Sunset Cruise",
        "nav_private": "Private Charter",
        "nav_gallery": "Gallery",
        "nav_review": "Reviews",
        "nav_faq": "FAQ",
        "nav_blog": "Blog",
        "nav_contact": "About & Contact",
        "footer_terms": "Terms & Conditions",
        "footer_fulfillment": "Fulfillment Policy",
        "footer_privacy": "Privacy Policy",
        "footer_about": "About",
    },
    "de": {
        "nav_morning": "Morgenrundfahrt",
        "nav_sunset": "Sonnenuntergangstour",
        "nav_private": "Privatcharter",
        "nav_gallery": "Galerie",
        "nav_review": "Bewertungen",
        "nav_faq": "Häufige Fragen",
        "nav_blog": "Blog",
        "nav_contact": "Kontakt & Über uns",
        "footer_terms": "AGB",
        "footer_fulfillment": "Erfüllungsrichtlinie",
        "footer_privacy": "Datenschutz",
        "footer_about": "Über uns",
    },
}


def locale_prefix(locale: str) -> str:
    return "" if locale == DEFAULT_LOCALE else f"/{locale}"


def localized_path(locale: str, path: str) -> str:
    path = path if path.startswith("/") else f"/{path}"
    if path == "/":
        return locale_prefix(locale) or "/"
    return f"{locale_prefix(locale)}{path}"


def public_page_url(locale: str, page_path: str) -> str:
    """User-facing URL matching the live WordPress site."""
    page_path = page_path if page_path.startswith("/") else f"/{page_path}"
    slug = page_path.strip("/").rstrip("/")
    if locale == "de":
        alias = REVERSE_DE_ALIASES.get(slug)
        if alias:
            return f"/de/{alias}/"
        return f"/de/{slug}/" if slug else "/de/"
    if slug == "chill-cruise":
        return "/cruise/"
    if slug == "contacts":
        return "/contacts-about/"
    return localized_path(locale, page_path)


def nav_for_locale(locale: str) -> list[dict[str, str]]:
    t = SITE_I18N.get(locale, SITE_I18N["en"])
    links = [
        {"title": t["nav_morning"], "url": public_page_url(locale, "/chill-cruise/")},
        {"title": t["nav_sunset"], "url": public_page_url(locale, "/sunset-cruise/")},
        {"title": t["nav_private"], "url": public_page_url(locale, "/private-charter/")},
        {"title": t["nav_gallery"], "url": public_page_url(locale, "/gallery/")},
        {"title": t["nav_review"], "url": public_page_url(locale, "/reviews/")},
        {"title": t["nav_faq"], "url": public_page_url(locale, "/faq/")},
    ]
    if locale == DEFAULT_LOCALE:
        links.append({"title": t["nav_blog"], "url": public_page_url(locale, "/blog/")})
    links.append({"title": t["nav_contact"], "url": public_page_url(locale, "/contacts/")})
    return links


def footer_nav_cols_for_locale(locale: str) -> list[list[dict[str, str]]]:
    t = SITE_I18N.get(locale, SITE_I18N["en"])
    return [
        [
            {"title": t["footer_about"], "url": public_page_url(locale, "/contacts/")},
            {"title": t["nav_gallery"], "url": public_page_url(locale, "/gallery/")},
        ],
        [
            {"title": t["nav_blog"], "url": public_page_url(locale, "/blog/")},
            {"title": t["nav_faq"], "url": public_page_url(locale, "/faq/")},
            {"title": t["nav_review"], "url": public_page_url(locale, "/reviews/")},
        ],
    ]


def footer_legal_for_locale(locale: str) -> list[dict[str, str]]:
    t = SITE_I18N.get(locale, SITE_I18N["en"])
    # Match prod footer: Terms + Fulfillment only (no Privacy Policy link).
    return [
        {"title": t["footer_terms"], "url": localized_path(locale, "/terms-conditions/")},
        {"title": t["footer_fulfillment"], "url": localized_path(locale, "/fulfillment-policy/")},
    ]
