from __future__ import annotations

from django.template.loader import render_to_string
from django.utils.html import strip_tags
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import BlogPost


class BlogLoadMoreView(APIView):
    authentication_classes: list = []
    permission_classes: list = []

    def post(self, request):
        page = max(int(request.data.get("page", 1)), 1)
        per_page = max(int(request.data.get("per_page", 9)), 1)
        max_pages = max(int(request.data.get("max_pages", 1)), 1)

        qs = BlogPost.objects.filter(is_published=True)
        total = qs.count()
        real_max = max((total + per_page - 1) // per_page, 1)
        start = (page - 1) * per_page
        posts = list(qs[start : start + per_page])

        if not posts:
            return Response({"success": False, "message": "No posts"}, status=status.HTTP_200_OK)

        html = render_to_string(
            "includes/blog_cards.html",
            {"posts": posts},
            request=request,
        )
        return Response(
            {
                "success": True,
                "data": {
                    "html": html,
                    "has_more": page < min(max_pages, real_max),
                },
            }
        )


class BlogPostDetailView(APIView):
    authentication_classes: list = []
    permission_classes: list = []

    def get(self, request, slug: str):
        try:
            post = BlogPost.objects.get(slug=slug, is_published=True)
        except BlogPost.DoesNotExist:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(
            {
                "title": post.title,
                "excerpt": post.excerpt,
                "body": post.body,
                "image_url": post.image_url,
                "published_at": post.published_at.isoformat(),
            }
        )
