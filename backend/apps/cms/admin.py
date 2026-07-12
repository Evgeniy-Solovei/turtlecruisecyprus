from django.contrib import admin
from unfold.admin import ModelAdmin

from .forms import BlogPostAdminForm, SitePageAdminForm
from .models import BlogPost, SiteConfig, SitePage


@admin.register(BlogPost)
class BlogPostAdmin(ModelAdmin):
    form = BlogPostAdminForm
    list_display = ("title", "slug", "is_published", "published_at", "updated_at")
    list_filter = ("is_published",)
    search_fields = ("title", "slug", "excerpt")
    readonly_fields = ("slug", "created_at", "updated_at")
    date_hierarchy = "published_at"
    fieldsets = (
        (
            "Статья",
            {
                "description": "После сохранения с галочкой «Опубликовано» статья появится в Blog на сайте.",
                "fields": ("title", "excerpt", "body"),
            },
        ),
        ("Обложка", {"fields": ("cover_image",)}),
        ("Публикация", {"fields": ("is_published", "published_at")}),
        ("Служебное", {"fields": ("slug", "created_at", "updated_at"), "classes": ("collapse",)}),
    )


@admin.register(SitePage)
class SitePageAdmin(ModelAdmin):
    form = SitePageAdminForm
    list_display = ("title", "locale", "slug", "is_published", "updated_at")
    list_filter = ("locale", "is_published")
    search_fields = ("slug", "title")
    readonly_fields = ("updated_at",)
    fieldsets = (
        (
            "Страница",
            {
                "description": "Основные страницы сайта (главная, круиз, FAQ…).",
                "fields": ("locale", "slug", "title", "is_published"),
            },
        ),
        ("Текст", {"fields": ("body_html",)}),
        ("SEO", {"fields": ("meta_description",), "classes": ("collapse",)}),
    )

    def get_exclude(self, request, obj=None):
        return ("wp_slug", "body_class")


@admin.register(SiteConfig)
class SiteConfigAdmin(ModelAdmin):
    list_display = ("key", "updated_at")

    def has_module_permission(self, request):
        return False
