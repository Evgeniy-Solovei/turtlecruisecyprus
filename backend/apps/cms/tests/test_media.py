from django.test import SimpleTestCase

from apps.cms.media import fix_media_urls_in_html, normalize_wp_media_path, resolve_attachment


class MediaPathTests(SimpleTestCase):
    def test_normalize_server_absolute_path(self):
        raw = "//home/ochihost/turtlecruisecyprus.com/www/wp-content/uploads/2026/05/rectangle-2.webp"
        self.assertEqual(normalize_wp_media_path(raw), "2026/05/rectangle-2.webp")

    def test_resolve_attachment_uses_normalized_path(self):
        media_map = {
            679: "//home/ochihost/turtlecruisecyprus.com/www/wp-content/uploads/2026/05/rectangle-2.webp"
        }
        self.assertEqual(resolve_attachment(media_map, 679), "/media/wp/2026/05/rectangle-2.webp")

    def test_fix_media_urls_in_html(self):
        html = '<img src="/media/wp/home/ochihost/turtlecruisecyprus.com/www/wp-content/uploads/2026/05/a.webp">'
        self.assertIn('/media/wp/2026/05/a.webp', fix_media_urls_in_html(html))

    def test_footer_icons_use_static(self):
        html = '<img src="/media/wp/2026/05/visa.svg">'
        fixed = fix_media_urls_in_html(html)
        self.assertIn('/static/frontend/img/dist/visa.svg', fixed)
        self.assertNotIn('/media/wp/', fixed)
