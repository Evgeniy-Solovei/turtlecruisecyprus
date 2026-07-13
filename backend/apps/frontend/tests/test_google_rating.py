from django.test import TestCase, override_settings

from apps.frontend.google_rating import get_site_rating


class GoogleRatingTests(TestCase):
    @override_settings(
        GOOGLE_RATING_SCORE="4.9",
        GOOGLE_REVIEW_COUNT="900",
        GOOGLE_MAPS_URL="https://example.com/maps",
        GOOGLE_PLACES_API_KEY="",
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            }
        },
    )
    def test_env_fallback(self):
        rating = get_site_rating()
        self.assertEqual(rating["score"], "4.9")
        self.assertEqual(rating["count"], 900)
        self.assertEqual(rating["label_en"], "Based on 900 reviews")
        self.assertEqual(rating["label_de"], "Basierend auf 900 Bewertungen")
        self.assertEqual(rating["url"], "https://example.com/maps")
