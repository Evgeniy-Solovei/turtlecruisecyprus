#!/usr/bin/env python3
"""Convert WP block render.php files to Django templates."""
from __future__ import annotations

import re
from pathlib import Path

WP_BLOCKS = Path(__file__).resolve().parents[2] / "turtlecruisebyscubacat/wp-content/themes/turtle/custom-blocks"
OUT = Path(__file__).resolve().parents[1] / "templates/blocks"

FIELD_MAP = {
    "block_id": "d.block_id",
    "anchor": "d.block_id",
    "title": "d.title",
    "subtitle": "d.subtitle",
    "subtitle_strong": "d.subtitle_strong",
    "bg_image": "d.bg_image",
    "bg_image_mob": "d.bg_image_mob",
    "bg_video": "d.bg_video",
    "rating_num": "d.rating_num",
    "rating_label": "d.rating_label",
    "rating_url": "d.rating_url",
    "choose_label": "d.choose_label",
    "tours": "d.tours",
    "items": "d.items",
    "columns": "d.columns",
    "footer_link": "d.footer_link",
    "locations": "d.locations",
    "image": "d.image",
    "image_mob": "d.image_mob",
    "link": "d.link",
    "note": "d.note",
    "desc": "d.desc",
    "slides": "d.slides",
    "rating_text": "d.rating_text",
    "rating_strong": "d.rating_strong",
    "global_stars": "d.stars_count",
    "stars_count": "d.stars_count",
    "instagram_url": "d.instagram_url",
    "instagram_handle": "d.instagram_handle",
    "btn_label_desk": "d.btn_label_desktop",
    "btn_label_mob": "d.btn_label_mobile",
    "btn_url": "d.btn_url",
    "card_title": "d.card_title",
    "card_image": "d.card_image",
    "card_time": "d.card_time",
    "card_desc": "d.card_desc",
    "card_price": "d.card_price",
    "card_link": "d.card_link",
    "visual_type": "d.visual_type",
    "slider_images": "d.slider_images",
    "lead": "d.lead",
    "content": "d.content",
    "final": "d.final",
    "cruise_open": "d.cruise_open2",
    "cruise_open_hero": "d.cruise_open2",
    "stats": "d.stats",
    "find_title": "d.find_title",
    "find_btns": "d.find_btns",
    "contact_title": "d.contact_title",
    "contact_desc": "d.contact_desc",
    "whatsapp": "d.whatsapp",
    "email": "d.email",
    "phone": "d.phone",
    "phone_raw": "d.phone|phone_digits",
    "breadcrumb": "d.breadcrumb",
    "footer_text": "d.footer_text",
    "title_em": "d.title_em",
    "desc_hl": "d.desc_highlight",
    "icon": "d.icon",
    "features": "d.features",
    "notes_text": "d.notes_text",
    "button_text": "d.button_text",
    "button_url": "d.button_url",
    "gallery": "d.gallery",
    "badges": "d.badges",
    "btn_filled_text": "d.btn_filled_text",
    "btn_filled_url": "d.btn_filled_url",
    "btn_outline_text": "d.btn_outline_text",
    "btn_outline_url": "d.btn_outline_url",
    "cards": "d.cards",
    "notes": "d.notes",
    "cta_text": "d.cta_text",
    "cta_link": "d.cta_link",
    "tagline": "d.tagline",
    "layout": "d.layout",
    "text": "d.text",
    "rating": "d.rating",
    "load_btn_label": "d.load_btn_label",
    "posts_per_page": "d.posts_per_page",
    "load_more_label": "d.load_more_label",
    "breadcrumb_page": "d.breadcrumb_page_label",
}

SAFE_HTML_FIELDS = {
    "title", "card_title", "t_title", "item_title", "card_title",
    "desc", "desc_hl", "desc_highlight", "rating", "rating_text",
    "lead", "content", "final", "note", "cta_text", "tagline",
    "tour.title", "item.title", "col_title",
}

SKIP_BLOCKS = set()


def extract_svgs(php: str) -> dict[str, str]:
    svgs = {}
    for m in re.finditer(r"\$(\w+_svg)\s*=\s*'((?:\\'|[^'])*)';", php, re.DOTALL):
        svgs[m.group(1)] = m.group(2).replace("\\'", "'")
    return svgs


def php_to_django(body: str, svgs: dict[str, str]) -> str:
    # Remove PHP blocks that are pure logic (assignments, functions, queries)
    body = re.sub(r"<\?php\s*\$bc_items.*?endif;\s*\?>", "", body, flags=re.DOTALL)
    body = re.sub(r"<\?php\s*\$col_configs.*?;\s*\?>", "", body, flags=re.DOTALL)
    body = re.sub(r"<\?php\s*\$columns\s*=.*?;\s*\?>", "", body, flags=re.DOTALL)
    body = re.sub(r"<\?php\s*\$top_locations.*?;\s*\?>", "", body, flags=re.DOTALL)
    body = re.sub(r"<\?php\s*\$bottom_locations.*?;\s*\?>", "", body, flags=re.DOTALL)
    body = re.sub(r"<\?php\s*\$query\s*=.*?;\s*\?>", "", body, flags=re.DOTALL)
    body = re.sub(r"<\?php\s*\$has_more\s*=.*?;\s*\?>", "", body, flags=re.DOTALL)
    body = re.sub(r"<\?php\s*function\s+render_review_card.*?}\s*\?>", "", body, flags=re.DOTALL)
    body = re.sub(r"<\?php\s*\$col1_items.*?;\s*\?>", "", body, flags=re.DOTALL)
    body = re.sub(r"<\?php\s*\$per_col_page.*?;\s*\?>", "", body, flags=re.DOTALL)
    body = re.sub(r"<\?php\s*\$total\s*=.*?;\s*\?>", "", body, flags=re.DOTALL)

    body = body.replace("<?= $anchor ? 'id=\"' . esc_attr($anchor) . '\"' : ''; ?>",
                        "{% if d.block_id %} id=\"{{ d.block_id }}\"{% endif %}")

    body = re.sub(
        r"bloginfo\('template_url'\)\s*\.\s*'/assets/img/dist/([^']+)'",
        r"{% static 'frontend/img/dist/\1' %}",
        body,
    )
    body = re.sub(
        r"get_template_directory_uri\(\)\s*\.\s*'/assets/img/dist/([^']+)'",
        r"{% static 'frontend/img/dist/\1' %}",
        body,
    )

    # wp_get_attachment_image
    def _img(m):
        var = m.group(1)
        classes = m.group(2) or ""
        alt = m.group(3) or ""
        cls = f' class="{classes}"' if classes else ""
        alt_attr = f' alt="{alt}"' if alt else ' alt=""'
        return f"{{% if {var} %}}<img src=\"{{% media {var} %}}\"{cls}{alt_attr}>{% endif %}}"

    body = re.sub(
        r"<\?php echo wp_get_attachment_image\(\$(\w+),\s*'[^']*',\s*false,\s*\['class'\s*=>\s*'([^']*)'(?:,\s*'alt'\s*=>\s*esc_attr\(\$(\w+)\))?\]\);\s*\?>",
        _img,
        body,
    )
    body = re.sub(
        r"<\?php echo wp_get_attachment_image\(\$(\w+),\s*'[^']*',\s*false\);\s*\?>",
        lambda m: f"{{% if {m.group(1)} %}}<img src=\"{{% media {m.group(1)} %}}\" alt=\"\">{{% endif %}}",
        body,
    )
    body = re.sub(
        r"<\?php echo wp_get_attachment_image\(\$(\w+),\s*'[^']*',\s*false,\s*\['alt'\s*=>\s*esc_attr\(\$(\w+)\)\]\);\s*\?>",
        lambda m: f"{{% if {m.group(1)} %}}<img src=\"{{% media {m.group(1)} %}}\" alt=\"\">{{% endif %}}",
        body,
    )
    body = re.sub(
        r"<\?php echo wp_get_attachment_image\(\$(\w+),\s*'large'\);\s*\?>",
        lambda m: f"{{% if {m.group(1)} %}}<img src=\"{{% media {m.group(1)} %}}\" alt=\"\">{{% endif %}}",
        body,
    )
    body = re.sub(
        r"wp_get_attachment_image_url\(\$(\w+),\s*'full'\)",
        r"{% media \1 %}",
        body,
    )

    # foreach / while loops
    body = re.sub(r"<\?php if \(have_rows\('items'\)\) : \?>", "{% if d.items %}", body)
    body = re.sub(r"<\?php while \(have_rows\('items'\)\) : the_row\(\);", "{% for item in d.items %}", body)
    body = re.sub(r"<\?php foreach \(\$columns as \$column\) :", "{% for column in d.columns %}", body)
    body = re.sub(r"<\?php foreach \(\$columns as \$col_i => \$col_items\) :", "{% guest_photo_columns d.items as photo_columns %}{% for offset, col_items in photo_columns %}", body)
    body = re.sub(r"<\?php foreach \(\$columns as \$col_index => \$col_items\) :", "{% gallery_masonry_columns d.items as gallery_columns %}{% for offset, col_items in gallery_columns %}", body)
    body = re.sub(r"<\?php foreach \(\$items as \$item\) :", "{% for item in d.items %}", body)
    body = re.sub(r"<\?php foreach \(\$items as \$i => \$item\) :", "{% for item in d.items %}", body)
    body = re.sub(r"<\?php foreach \(\$tours as \$tour\) :", "{% for tour in d.tours %}", body)
    body = re.sub(r"<\?php foreach \(\$slides as \$slide\) :", "{% for slide in d.slides %}", body)
    body = re.sub(r"<\?php foreach \(\$locations as \$i => \$loc\) :", "{% for loc in d.locations %}", body)
    body = re.sub(r"<\?php foreach \(\$top_locations as \$i => \$loc\) :", "{% for loc in d.locations %}", body)
    body = re.sub(r"<\?php foreach \(\$bottom_locations as \$i => \$loc\) :", "{% for loc in d.locations %}{% if forloop.counter|divisibleby:2 %}", body)
    body = re.sub(r"<\?php foreach \(\$stats as \$stat\) :", "{% for stat in d.stats %}", body)
    body = re.sub(r"<\?php foreach \(\$find_btns as \$btn\) :", "{% for btn in d.find_btns %}", body)
    body = re.sub(r"<\?php foreach \(\$slider_images as \$img_id\) :", "{% for img_id in d.slider_images %}", body)
    body = re.sub(r"<\?php foreach \(\$cards as \$card\) :", "{% for card in d.cards %}", body)
    body = re.sub(r"<\?php foreach \(\$features as \$feature\) :", "{% for feature in d.features %}", body)
    body = re.sub(r"<\?php foreach \(\$gallery as \$image\) :", "{% for image in d.gallery %}", body)
    body = re.sub(r"<\?php foreach \(\$badges as \$badge\) :", "{% for badge in d.badges %}", body)
    body = re.sub(r"<\?php foreach \(\$notes as \$note_item\) :", "{% for note_item in d.notes %}", body)
    body = re.sub(r"<\?php foreach \(\$col_items as \$item\) :", "{% for item in col_items %}", body)
    body = re.sub(r"<\?php foreach \(\$column\['items'\] as \$item\) :", "{% for item in column.items %}", body)
    body = re.sub(r"<\?php foreach \(\$items as \$item\) :\s*\n\s*\$question", "{% for item in column.items %}\n\t\t\t\t\t\t\t{% with question", body)

    body = re.sub(r"<\?php endforeach; \?>", "{% endfor %}", body)
    body = re.sub(r"<\?php endwhile; \?>", "{% endfor %}", body)

    # if / endif
    body = re.sub(r"<\?php if \(\$(\w+)\) : \?>", r"{% if \1 %}", body)
    body = re.sub(r"<\?php if \(\$(\w+) \|\| \$(\w+)\) : \?>", r"{% if \1 or \2 %}", body)
    body = re.sub(r"<\?php if \(\$(\w+) && \$(\w+)\) : \?>", r"{% if \1 and \2 %}", body)
    body = re.sub(r"<\?php elseif \(\$(\w+)\) : \?>", r"{% elif \1 %}", body)
    body = re.sub(r"<\?php else : \?>", "{% else %}", body)
    body = re.sub(r"<\?php endif; \?>", "{% endif %}", body)

    # echo statements
    body = re.sub(r"<\?php echo esc_html\(\$(\w+)\); \?>", r"{{ \1 }}", body)
    body = re.sub(r"<\?php echo esc_attr\(\$(\w+)\); \?>", r"{{ \1 }}", body)
    body = re.sub(r"<\?php echo esc_url\(\$(\w+)\); \?>", r"{{ \1 }}", body)
    body = re.sub(r"<\?php echo esc_url\(\$(\w+)\['url'\]\); \?>", r"{{ \1.url }}", body)
    body = re.sub(r"<\?php echo esc_html\(\$(\w+)\['title'\]\); \?>", r"{{ \1.title }}", body)
    body = re.sub(r"<\?php echo esc_html\(\$(\w+)\['label'\]\); \?>", r"{{ \1.label }}", body)
    body = re.sub(r"<\?php echo esc_html\(\$(\w+)\['number'\]\); \?>", r"{{ \1.number }}", body)
    body = re.sub(r"<\?php echo esc_html\(\$(\w+)\['question'\]\); \?>", r"{{ \1.question }}", body)
    body = re.sub(r"<\?php echo esc_html\(\$(\w+)\['answer'\]\); \?>", r"{{ \1.answer }}", body)
    body = re.sub(r"<\?php echo esc_html\(\$(\w+)\['quote'\]\); \?>", r"{{ \1.quote }}", body)
    body = re.sub(r"<\?php echo esc_html\(\$(\w+)\['name'\]\); \?>", r"{{ \1.name }}", body)
    body = re.sub(r"<\?php echo esc_html\(\$(\w+)\['location'\]\); \?>", r"{{ \1.location }}", body)
    body = re.sub(r"<\?php echo esc_html\(\$(\w+)\['time'\]\); \?>", r"{{ \1.time }}", body)
    body = re.sub(r"<\?php echo esc_html\(\$(\w+)\['desc'\]\); \?>", r"{{ \1.desc }}", body)
    body = re.sub(r"<\?php echo esc_html\(\$(\w+)\['price'\]\); \?>", r"{{ \1.price }}", body)
    body = re.sub(r"<\?php echo esc_html\(\$(\w+)\['btn_label'\]\); \?>", r"{{ \1.btn_label }}", body)
    body = re.sub(r"<\?php echo esc_html\(\$(\w+)\['title'\]\); \?>", r"{{ \1.title }}", body)
    body = re.sub(r"<\?php echo esc_html\(\$(\w+)\['text'\]\); \?>", r"{{ \1.text }}", body)
    body = re.sub(r"<\?php echo esc_html\(\$(\w+)\['lead'\]\); \?>", r"{{ \1.lead }}", body)
    body = re.sub(r"<\?php echo \$(\w+); \?>", r"{{ \1|safe }}", body)
    body = re.sub(r"<\?php echo nl2br\(\$(\w+)\); \?>", r"{{ \1|linebreaksbr }}", body)
    body = re.sub(r"<\?php echo \$link \? esc_html\(\$link\['title'\]\) : 'Watch Video'; \?>", r"{{ item.link.title|default:'Watch Video' }}", body)

    # SVG echoes
    for name, svg in svgs.items():
        body = body.replace(f"<?php echo ${name}; ?>", svg)
        body = body.replace(f"<?php echo ${name} ?>", svg)

    # variable assignments in loops - map to item.*
    loop_vars = [
        ("image", "item.image"), ("card_title", "item.title"), ("lead", "item.lead"),
        ("text", "item.text"), ("link", "item.link"), ("video_url", "item.video_url"),
        ("title", "item.title"), ("time", "item.time"), ("desc", "item.desc"),
        ("price", "item.price"), ("btn_label", "item.btn_label"), ("cruise_open", "item.booking_trigger"),
        ("card_link", "item.card_link"), ("col_title", "column.title"), ("items", "column.items"),
        ("question", "item.question"), ("answer", "item.answer"),
        ("stars", "item.stars"), ("quote", "item.quote"), ("name", "item.name"),
        ("location", "item.location"), ("s_title", "slide.title"), ("s_text", "slide.text"),
        ("photo", "loc.image"), ("photo_mob", "loc.image_mob"), ("idx", "forloop.counter"),
        ("size", "item.size"), ("alt", "item.alt"), ("item_title", "item.title"),
        ("item_text", "item.text"), ("t_image", "tour.image"), ("t_title", "tour.title"),
        ("t_time", "tour.time"), ("t_desc", "tour.desc"), ("t_price", "tour.price"),
        ("t_url", "tour.url"), ("t_cruise_open", "tour.cruise_open"),
    ]
    body = re.sub(r"<\?php\s+\$\w+ = .*?;\s*\?>", "", body)

    # Map $var to d.var in conditions and outputs
    for php_var, django_var in FIELD_MAP.items():
        body = re.sub(rf"\${php_var}\b", django_var, body)

    # item/subfield dict access
    body = re.sub(r"(\w+)\['url'\]", r"\1.url", body)
    body = re.sub(r"(\w+)\['target'\]", r"\1.target", body)
    body = re.sub(r"(\w+)\['title'\]", r"\1.title", body)
    body = re.sub(r"(\w+)\['label'\]", r"\1.label", body)
    body = re.sub(r"(\w+)\['image'\]", r"\1.image", body)
    body = re.sub(r"(\w+)\['image_mob'\]", r"\1.image_mob", body)
    body = re.sub(r"(\w+)\['number'\]", r"\1.number", body)

    # Clean remaining PHP
    body = re.sub(r"<\?php.*?\?>", "", body, flags=re.DOTALL)

    # Fix data-index
    body = body.replace('data-index="<?= $idx; ?>"', 'data-index="{{ forloop.counter }}"')
    body = body.replace("<?= $idx === 1 ? 'active' : ''; ?>", "{% if forloop.first %}active{% endif %}")
    body = body.replace('class="route__photo <?= $idx === 1 ? \'active\' : \'\'; ?>"',
                        'class="route__photo{% if forloop.first %} active{% endif %}"')

    body = re.sub(r"\n{3,}", "\n\n", body)
    return body.strip()


def convert_block(block_dir: Path) -> str:
    php_file = block_dir / "render.php"
    php = php_file.read_text(encoding="utf-8")
    svgs = extract_svgs(php)
    if "?>" in php:
        body = php.split("?>", 1)[1]
    else:
        body = php
    body = php_to_django(body, svgs)
    header = "{% load cms_extras static %}\n"
    return header + body + "\n"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for block_dir in sorted(WP_BLOCKS.glob("block-*")):
        name = block_dir.name + ".html"
        if block_dir.name in SKIP_BLOCKS:
            continue
        out_path = OUT / name
        try:
            content = convert_block(block_dir)
            out_path.write_text(content, encoding="utf-8")
            print(f"OK {name}")
        except Exception as exc:
            print(f"FAIL {name}: {exc}")


if __name__ == "__main__":
    main()
