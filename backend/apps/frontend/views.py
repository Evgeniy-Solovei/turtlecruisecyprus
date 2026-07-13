from __future__ import annotations

from urllib.parse import urlencode

from django.http import Http404, HttpResponsePermanentRedirect
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import TemplateView

from apps.cms.models import BlogPost, SitePage
from apps.cms.media import fix_media_urls_in_html

from .i18n import DEFAULT_LOCALE, SITE_I18N, localized_path
from .seo import build_seo_meta
from .site_data import PAGES, REDIRECTS


def _resolve_path(request) -> str:
    path = request.path_info.lstrip("/")
    locale = getattr(request, "locale", DEFAULT_LOCALE)
    if locale != DEFAULT_LOCALE and (path == "de" or path.startswith("de/")):
        path = path[3:] if path.startswith("de/") else ""
    return path if path.endswith("/") or not path else f"{path}/"


MIN_IMPORTED_BODY = 2000
RESERVED_SLUGS = {key.rstrip("/") for key in PAGES} | {key.rstrip("/") for key in REDIRECTS}


def _localized_content_partial(locale: str, partial: str) -> str:
    if not partial or locale == DEFAULT_LOCALE:
        return partial
    from django.conf import settings

    candidate = partial.replace("pages/wp/", f"pages/wp/{locale}/")
    if (settings.BASE_DIR / "templates" / candidate).is_file():
        return candidate
    return partial


def _page_context(request, path: str) -> dict:
    locale = getattr(request, "locale", DEFAULT_LOCALE)
    slug = path.rstrip("/")
    entry = PAGES.get(path)
    if not entry:
        raise Http404

    template_name, body_class, content_partial = entry
    content_partial = _localized_content_partial(locale, content_partial)
    ctx: dict = {
        "body_class": body_class,
        "content_partial": content_partial,
        "page_html": "",
        "page_title": "",
        "current_path": localized_path(locale, path if path else "/"),
    }

    site_page = SitePage.objects.filter(locale=locale, slug=slug, is_published=True).first()
    use_imported = bool(
        site_page
        and site_page.body_html.strip()
        and (len(site_page.body_html) >= MIN_IMPORTED_BODY or slug == "blog")
    )
    if use_imported and site_page:
        ctx["page_html"] = fix_media_urls_in_html(site_page.body_html)
        if slug == "gallery":
            ctx["page_html"] = (
                ctx["page_html"]
                .replace("gallery-load gallery__masonry", "gallery__masonry gallery__masonry--static")
                .replace('class="gallery-load gallery__masonry"', 'class="gallery__masonry gallery__masonry--static"')
            )
        ctx["page_title"] = site_page.title
        ctx["body_class"] = site_page.body_class or body_class
        ctx["content_partial"] = ""
    elif site_page:
        ctx["page_title"] = site_page.title
    elif slug == "privacy-policy":
        ctx["page_title"] = SITE_I18N.get(locale, SITE_I18N["en"])["footer_privacy"]
    elif slug == "terms-conditions":
        ctx["page_title"] = SITE_I18N.get(locale, SITE_I18N["en"])["footer_terms"]
    elif slug == "fulfillment-policy":
        ctx["page_title"] = SITE_I18N.get(locale, SITE_I18N["en"])["footer_fulfillment"]

    from django.conf import settings

    if (
        not ctx["page_html"]
        and content_partial
        and getattr(settings, "CMS_DISABLE_TEMPLATE_FALLBACK", False)
        and slug != "blog"
    ):
        raise Http404(f"CMS snapshot missing content for /{slug or ''}")

    if slug == "blog" and not ctx["page_html"]:
        ctx["content_partial"] = "includes/blog_listing.html"
        ctx["page_title"] = ctx["page_title"] or "Blog"

    seo_title = ctx["page_title"] or "Turtle Cruise Cyprus"
    seo_description = ""
    if site_page and site_page.meta_description:
        seo_description = site_page.meta_description
    ctx["seo"] = build_seo_meta(
        request,
        title=f"{seo_title} — Turtle Cruise Cyprus" if seo_title != "Turtle Cruise Cyprus" else seo_title,
        description=seo_description,
    )

    return template_name, ctx


@method_decorator(ensure_csrf_cookie, name="dispatch")
class SitePageView(TemplateView):
    def dispatch(self, request, *args, **kwargs):
        path = kwargs.get("path", _resolve_path(request))
        if path not in PAGES and path.rstrip("/") + "/" in REDIRECTS:
            return redirect("/" + REDIRECTS[path.rstrip("/") + "/"], permanent=True)
        return super().dispatch(request, *args, **kwargs)

    def get_template_names(self):
        path = self.kwargs.get("path", _resolve_path(self.request))
        template_name, _ = _page_context(self.request, path)
        return [template_name]

    def get_context_data(self, **kwargs):
        path = self.kwargs.get("path", _resolve_path(self.request))
        _, ctx = _page_context(self.request, path)
        base = super().get_context_data(**kwargs)
        base.update(ctx)
        return base


@method_decorator(ensure_csrf_cookie, name="dispatch")
class HomeView(SitePageView):
    def get_template_names(self):
        template_name, _ = _page_context(self.request, "")
        return [template_name]

    def get_context_data(self, **kwargs):
        _, ctx = _page_context(self.request, "")
        base = super().get_context_data(**kwargs)
        base.update(ctx)
        return base


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ThankYouView(SitePageView):
    def get_template_names(self):
        return [PAGES["thank-you/"][0]]

    def get_context_data(self, **kwargs):
        base = super().get_context_data(**kwargs)
        _, ctx = _page_context(self.request, "thank-you/")
        base.update(ctx)
        return base


@method_decorator(ensure_csrf_cookie, name="dispatch")
class BlogPostView(TemplateView):
    template_name = "pages/blog_post.html"

    def get_context_data(self, **kwargs):
        locale = getattr(self.request, "locale", DEFAULT_LOCALE)
        slug = kwargs.get("slug", "")
        post = BlogPost.objects.filter(slug=slug, is_published=True).first()
        if not post:
            raise Http404
        related = list(
            BlogPost.objects.filter(is_published=True)
            .exclude(pk=post.pk)
            .order_by("-published_at")[:3]
        )
        post_path = localized_path(locale, f"/{slug}/")
        base = super().get_context_data(**kwargs)
        base.update(
            {
                "post": post,
                "related_posts": related,
                "page_title": post.title,
                "blog_url": localized_path(locale, "/blog/"),
                "current_path": post_path,
                "seo": build_seo_meta(
                    self.request,
                    title=f"{post.title} — Turtle Cruise Cyprus",
                    description=post.excerpt,
                    og_type="article",
                    og_image=post.image_url,
                    published_at=post.published_at.isoformat() if post.published_at else "",
                ),
            }
        )
        return base


@method_decorator(ensure_csrf_cookie, name="dispatch")
class BlogPostRootView(BlogPostView):
    def dispatch(self, request, slug: str, *args, **kwargs):
        if slug in RESERVED_SLUGS:
            raise Http404
        if not BlogPost.objects.filter(slug=slug, is_published=True).exists():
            raise Http404
        return super().dispatch(request, slug=slug, *args, **kwargs)


def blog_legacy_redirect(request, slug: str):
    locale = getattr(request, "locale", DEFAULT_LOCALE)
    return HttpResponsePermanentRedirect(localized_path(locale, f"/{slug}/"))


def booking_return_redirect(request):
    locale = getattr(request, "locale", DEFAULT_LOCALE)
    public_id = request.GET.get("tc_booking_return") or ""
    session_id = request.GET.get("session_id") or ""
    thank_you = localized_path(locale, "/thank-you/")
    query: dict[str, str] = {}
    if public_id:
        query["booking_id"] = public_id
    if session_id:
        query["session_id"] = session_id
    if query:
        thank_you = f"{thank_you}?{urlencode(query)}"
    return redirect(thank_you)


def page_not_found(request, exception):
    return render(request, "pages/not_found.html", status=404)


def legacy_redirect(request, target: str):
    locale = getattr(request, "locale", DEFAULT_LOCALE)
    return HttpResponsePermanentRedirect(localized_path(locale, f"/{target}"))
