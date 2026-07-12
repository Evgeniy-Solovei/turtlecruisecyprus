from __future__ import annotations

from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class SitePage(models.Model):
    locale = models.CharField(max_length=5, default="en")
    slug = models.SlugField(max_length=120)
    wp_slug = models.SlugField(max_length=120, blank=True)
    title = models.CharField(max_length=255, blank=True)
    body_html = models.TextField(blank=True)
    body_class = models.CharField(max_length=80, blank=True)
    meta_description = models.TextField(blank=True)
    is_published = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("locale", "slug")]
        ordering = ["locale", "slug"]
        verbose_name = "Страница сайта"
        verbose_name_plural = "Страницы сайта"

    def __str__(self) -> str:
        return f"[{self.locale}] {self.slug}"


class SiteConfig(models.Model):
    key = models.CharField(max_length=120, unique=True)
    value = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.key


class BlogPost(models.Model):
    title = models.CharField("Заголовок", max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    excerpt = models.TextField("Короткое описание", blank=True)
    body = models.TextField("Текст статьи", blank=True)
    cover_image = models.ImageField("Обложка", upload_to="blog/%Y/%m/", blank=True)
    cover_image_static = models.CharField(
        max_length=255,
        blank=True,
        help_text="Static path under frontend/img/, e.g. dist/blog-1.jpg",
    )
    hero_image = models.CharField(
        max_length=512,
        blank=True,
        help_text="Legacy URL from WordPress import",
    )
    is_published = models.BooleanField(default=True)
    published_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-published_at"]
        verbose_name = "Статья блога"
        verbose_name_plural = "Статьи блога"

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._build_unique_slug(self.title)
        super().save(*args, **kwargs)

    def _build_unique_slug(self, title: str) -> str:
        base = slugify(title)[:200] or "post"
        slug = base
        counter = 2
        while BlogPost.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f"{base}-{counter}"
            counter += 1
        return slug

    @property
    def image_url(self) -> str:
        if self.cover_image:
            return self.cover_image.url
        if self.hero_image:
            return self.hero_image
        if self.cover_image_static:
            return f"/static/frontend/img/{self.cover_image_static.lstrip('/')}"
        return ""
