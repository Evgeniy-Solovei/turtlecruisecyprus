from __future__ import annotations

# Django route path → (template wrapper, body_class, static content partial)
PAGES = {
    "": ("pages/page.html", "home", "pages/wp/home_content.html"),
    "chill-cruise/": ("pages/page.html", "chill-cruise", "pages/wp/chill-cruise_content.html"),
    "sunset-cruise/": ("pages/page.html", "sunset-cruise", "pages/wp/sunset-cruise_content.html"),
    "private-charter/": ("pages/page.html", "private-charter", "pages/wp/private-charter_content.html"),
    "about/": ("pages/page.html", "about", "pages/wp/about_content.html"),
    "contacts/": ("pages/page.html", "contacts", "pages/wp/contacts_content.html"),
    "faq/": ("pages/page.html", "faq", "pages/wp/faq_content.html"),
    "gallery/": ("pages/page.html", "gallery", "pages/wp/gallery_content.html"),
    "reviews/": ("pages/page.html", "reviews", "pages/wp/reviews_content.html"),
    "blog/": ("pages/page.html", "blog", "pages/wp/blog_content.html"),
    "thank-you/": ("pages/thank_you.html", "thank-you", ""),
    "privacy-policy/": ("pages/legal.html", "legal", ""),
    "terms-conditions/": ("pages/legal.html", "legal", ""),
    "fulfillment-policy/": ("pages/legal.html", "legal", ""),
}

REDIRECTS = {
    "cruise/": "chill-cruise/",
    "contacts-about/": "contacts/",
    "terms/": "terms-conditions/",
    "terms-conditions-2/": "terms-conditions/",
}
