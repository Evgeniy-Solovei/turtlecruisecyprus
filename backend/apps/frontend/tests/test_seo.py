from __future__ import annotations

from django.test import TestCase

from apps.cms.models import BlogPost
from apps.frontend.i18n import language_switch_url


class FrontendSeoTests(TestCase):
    def test_sitemap_and_robots(self):
        sitemap = self.client.get("/sitemap.xml")
        self.assertEqual(sitemap.status_code, 200)
        self.assertIn("urlset", sitemap.content.decode())

        robots = self.client.get("/robots.txt")
        self.assertEqual(robots.status_code, 200)
        self.assertIn("Sitemap:", robots.content.decode())

    def test_blog_root_url_and_legacy_redirect(self):
        BlogPost.objects.create(
            title="How to see turtles",
            slug="how-to-see-turtles-in-cyprus",
            excerpt="Guide",
            body="<p>Guide</p>",
            is_published=True,
        )
        root = self.client.get("/how-to-see-turtles-in-cyprus/")
        self.assertEqual(root.status_code, 200)

        legacy = self.client.get("/blog/how-to-see-turtles-in-cyprus/")
        self.assertEqual(legacy.status_code, 301)
        self.assertEqual(legacy["Location"], "/how-to-see-turtles-in-cyprus/")

    def test_terms_conditions_2_redirect(self):
        response = self.client.get("/terms-conditions-2/")
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response["Location"], "/terms-conditions/")

    def test_language_switch_de_to_en_cruise(self):
        url = language_switch_url("de", "en", "/de/morgenrundfahrt/")
        self.assertEqual(url, "/chill-cruise/")
