from __future__ import annotations

import shutil
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


def _resolve_uploads_dir(source: str | None) -> Path | None:
    if source:
        path = Path(source).expanduser().resolve()
        if path.is_dir():
            if path.name == "uploads":
                return path
            nested = path / "wp-content" / "uploads"
            if nested.is_dir():
                return nested
            return path
        raise CommandError(f"Source not found: {path}")

    candidates = [
        Path("/tmp/turtlecruisebyscubacat/wp-content/uploads"),
        Path(settings.BASE_DIR).parent / "turtlecruisebyscubacat/wp-content/uploads",
        Path(settings.BASE_DIR).parent.parent / "turtlecruisebyscubacat/wp-content/uploads",
    ]
    for path in candidates:
        if path.is_dir():
            return path
    return None


class Command(BaseCommand):
    help = "Copy WordPress uploads into backend/media/wp (prod images)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            help="Path to wp-content/uploads or turtlecruisebyscubacat folder",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only report what would be copied",
        )

    def handle(self, *args, **options):
        uploads = _resolve_uploads_dir(options.get("source"))
        if not uploads:
            raise CommandError(
                "WP uploads not found. Pass --source /path/to/wp-content/uploads "
                "(from the full WP dump package)."
            )

        target = Path(settings.MEDIA_ROOT) / "wp"
        target.mkdir(parents=True, exist_ok=True)

        copied = 0
        skipped = 0
        for src in uploads.rglob("*"):
            if not src.is_file():
                continue
            rel = src.relative_to(uploads)
            dest = target / rel
            if dest.is_file() and dest.stat().st_size == src.stat().st_size:
                skipped += 1
                continue
            if options["dry_run"]:
                copied += 1
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            copied += 1

        total = sum(1 for _ in target.rglob("*") if _.is_file())
        self.stdout.write(f"Source: {uploads}")
        self.stdout.write(f"Target: {target}")
        if options["dry_run"]:
            self.stdout.write(self.style.WARNING(f"Dry run: would copy {copied} files ({skipped} unchanged)"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Copied {copied} files ({skipped} unchanged). Total in media/wp: {total}"))
