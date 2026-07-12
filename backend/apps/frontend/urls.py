from django.urls import path, re_path

from . import views
from .i18n import DE_URL_ALIASES
from .site_data import PAGES, REDIRECTS

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("thank-you/", views.ThankYouView.as_view(), name="thank-you"),
    path("booking-return/", views.booking_return_redirect, name="booking-return"),
    path("blog/<slug:slug>/", views.blog_legacy_redirect, name="blog-post-legacy"),
]

for page_path, _entry in PAGES.items():
    if not page_path or page_path in {"thank-you/"}:
        continue
    name = page_path.rstrip("/").replace("/", "-") or "home"
    urlpatterns.append(path(page_path, views.SitePageView.as_view(), {"path": page_path}, name=name))

for src, dst in REDIRECTS.items():
    urlpatterns.append(path(src, views.legacy_redirect, {"target": dst}, name=f"redirect-{dst.rstrip('/')}"))

de_patterns = [path("de/", views.HomeView.as_view(), name="de-home")]
de_patterns.append(path("de/thank-you/", views.ThankYouView.as_view(), name="de-thank-you"))
de_patterns.append(path("de/booking-return/", views.booking_return_redirect, name="de-booking-return"))
de_patterns.append(path("de/blog/<slug:slug>/", views.blog_legacy_redirect, name="de-blog-post-legacy"))
for page_path, _entry in PAGES.items():
    if not page_path or page_path in {"thank-you/"}:
        continue
    name = "de-" + (page_path.rstrip("/").replace("/", "-") or "home")
    de_patterns.append(path(f"de/{page_path}", views.SitePageView.as_view(), {"path": page_path}, name=name))
for src, dst in REDIRECTS.items():
    de_patterns.append(path(f"de/{src}", views.legacy_redirect, {"target": dst}, name=f"de-redirect-{dst.rstrip('/')}"))

for alias, page_path in DE_URL_ALIASES.items():
    de_patterns.append(
        path(f"de/{alias}/", views.SitePageView.as_view(), {"path": page_path}, name=f"de-alias-{alias}")
    )

urlpatterns += de_patterns

urlpatterns += [
    re_path(r"^(?P<slug>[\w-]+)/$", views.BlogPostRootView.as_view(), name="blog-post-root"),
    re_path(r"^de/(?P<slug>[\w-]+)/$", views.BlogPostRootView.as_view(), name="de-blog-post-root"),
]
