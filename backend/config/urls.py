from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from config.admin_setup import configure_admin_site

configure_admin_site()

from apps.bookings.compat_views import wordpress_admin_ajax

from apps.frontend.sitemaps import robots_txt, sitemap_xml

urlpatterns = [
    path("admin/", admin.site.urls),
    path("sitemap.xml", sitemap_xml, name="sitemap"),
    path("robots.txt", robots_txt, name="robots"),
    path("wp-admin/admin-ajax.php", wordpress_admin_ajax),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/v1/cruises/", include("apps.cruises.urls")),
    path("api/v1/bookings/", include("apps.bookings.urls")),
    path("api/v1/payments/", include("apps.payments.urls")),
    path("api/v1/audit/", include("apps.audit.urls")),
    path("api/v1/blog/", include("apps.cms.urls")),
    path("", include("apps.frontend.urls")),
]

handler404 = "apps.frontend.views.page_not_found"

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
