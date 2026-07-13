from django.core.cache import cache
from django.test import TestCase, override_settings

from apps.frontend.google_rating import CACHE_KEY, get_site_rating


class GoogleRatingTests(TestCase):
    def setUp(self):
        cache.delete(CACHE_KEY)

    @override_settings(
        GOOGLE_RATING_SCORE="4.9",
        GOOGLE_REVIEW_COUNT=900,
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

    @override_settings(
        GOOGLE_RATING_SCORE="4.9",
        GOOGLE_REVIEW_COUNT=840,
        GOOGLE_PLACES_API_KEY="fake-key",
        GOOGLE_PLACE_ID="ChIJtest",
        GOOGLE_RATING_USE_LIVE_API=False,
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            }
        },
    )
    def test_api_key_ignored_without_live_flag(self):
        rating = get_site_rating()
        self.assertEqual(rating["count"], 840)
        self.assertEqual(rating["source"], "env")
