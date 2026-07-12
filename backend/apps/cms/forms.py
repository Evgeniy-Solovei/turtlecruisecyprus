from django import forms
from unfold.contrib.forms.widgets import WysiwygWidget
from unfold.widgets import UnfoldAdminTextareaWidget, UnfoldAdminTextInputWidget

from .models import BlogPost, SitePage


class BlogPostAdminForm(forms.ModelForm):
    class Meta:
        model = BlogPost
        fields = [
            "title",
            "excerpt",
            "body",
            "cover_image",
            "is_published",
            "published_at",
        ]
        widgets = {
            "title": UnfoldAdminTextInputWidget(attrs={"placeholder": "Например: Лучший круиз на Кипре летом"}),
            "excerpt": UnfoldAdminTextareaWidget(
                attrs={"rows": 3, "placeholder": "Короткое описание для списка статей"}
            ),
            "body": WysiwygWidget(),
        }
        help_texts = {
            "title": "Заголовок статьи — виден на сайте.",
            "excerpt": "2–3 предложения — показываются в списке блога.",
            "body": "Основной текст. Панель сверху: жирный, списки, ссылки.",
            "cover_image": "Фото в начале статьи. JPG или PNG, до 5 МБ.",
            "is_published": "Без галочки статья сохранится как черновик.",
            "published_at": "Дата в списке статей.",
        }


class SitePageAdminForm(forms.ModelForm):
    class Meta:
        model = SitePage
        fields = ["locale", "slug", "title", "body_html", "meta_description", "is_published"]
        widgets = {
            "title": UnfoldAdminTextInputWidget(),
            "body_html": WysiwygWidget(),
            "meta_description": UnfoldAdminTextareaWidget(attrs={"rows": 2}),
        }
        help_texts = {
            "locale": "en — английская версия, de — немецкая.",
            "slug": "Технический адрес (cruise, gallery, faq…). Менять только если знаете зачем.",
            "title": "Заголовок вкладки браузера.",
            "body_html": "Текст страницы — редактор, без HTML вручную.",
            "meta_description": "Для поисковиков (необязательно).",
            "is_published": "Снять галочку — страница временно скрыта.",
        }
