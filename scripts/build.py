#!/usr/bin/env python3
"""data/episodes.json から静的な HTML と一覧用サムネイルを生成する。

公開そのものにこのスクリプトは不要です。生成済みの HTML を GitHub Pages が配信します。
法話を追加・修正したときだけ実行してください。手順は README.md にあります。
"""

from __future__ import annotations

import html
import json
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "episodes.json"
IMAGES = ROOT / "images"
THUMBS = IMAGES / "thumbs"

THUMB_MAX_WIDTH = 640
THUMB_QUALITY = 76
FULL_MAX_WIDTH = 1300

IMAGE_RE = re.compile(r"^[a-z0-9][a-z0-9-]*\.jpg$")
DATE_RE = re.compile(r"^(\d{4})年(\d{1,2})月(\d{1,2})日$")

FONT_LINKS = """<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500&family=Noto+Serif+JP:wght@400;600&family=Shippori+Mincho:wght@500;600&display=swap" rel="stylesheet">"""


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(1)


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def load_data() -> dict:
    try:
        data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail(f"見つかりません: {DATA_PATH}")
    except json.JSONDecodeError as exc:
        fail(f"data/episodes.json を読めません: {exc}")
    if not isinstance(data, dict):
        fail("data/episodes.json の先頭はオブジェクトにしてください。")
    return data


def require_str(obj: dict, key: str, where: str) -> str:
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip():
        fail(f"{where} の {key} が空です。")
    return value.strip()


def iso_date(date: str, where: str) -> str:
    match = DATE_RE.fullmatch(date)
    if not match:
        fail(f"{where} の date は「2026年11月13日」の形で書いてください: {date}")
    year, month, day = (int(part) for part in match.groups())
    return f"{year:04d}-{month:02d}-{day:02d}"


def jpeg_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as handle:
        if handle.read(2) != b"\xff\xd8":
            fail(f"JPEG ではありません: {path}")
        while True:
            marker_prefix = handle.read(1)
            if marker_prefix == b"":
                break
            if marker_prefix != b"\xff":
                continue
            marker = handle.read(1)
            while marker == b"\xff":
                marker = handle.read(1)
            if marker == b"":
                break
            code = marker[0]
            if code in (0xC0, 0xC1, 0xC2):
                handle.read(3)
                height, width = struct.unpack(">HH", handle.read(4))
                return width, height
            if code == 0xD9 or code == 0xDA:
                break
            if code == 0x01 or 0xD0 <= code <= 0xD9:
                continue
            length_bytes = handle.read(2)
            if len(length_bytes) < 2:
                break
            length = struct.unpack(">H", length_bytes)[0]
            handle.read(length - 2)
    fail(f"画像の寸法を読めません: {path}")
    return (0, 0)


def make_thumb(src: Path, dest: Path) -> tuple[int, int]:
    try:
        from PIL import Image
    except ImportError:
        fail("一覧のサムネイルを作るには Pillow が必要です。pip install -r requirements.txt を実行してください。")
    resample = getattr(Image, "Resampling", Image).LANCZOS
    with Image.open(src) as image:
        image = image.convert("RGB")
        if image.width > THUMB_MAX_WIDTH:
            height = round(image.height * THUMB_MAX_WIDTH / image.width)
            image = image.resize((THUMB_MAX_WIDTH, height), resample)
        dest.parent.mkdir(parents=True, exist_ok=True)
        image.save(dest, "JPEG", quality=THUMB_QUALITY, optimize=True, progressive=True)
        return image.width, image.height


def validate(data: dict) -> tuple[dict, list[dict]]:
    site = data.get("site")
    episodes = data.get("episodes")
    if not isinstance(site, dict):
        fail("site オブジェクトがありません。")
    if not isinstance(episodes, list):
        fail("episodes は配列にしてください。")
    require_str(site, "title", "site")
    url = require_str(site, "url", "site")
    if not url.startswith("https://"):
        fail("site.url は https:// から始めてください。")
    notes = site.get("notes")
    if not isinstance(notes, list) or not notes:
        fail("site.notes に、フッターへ載せる注記を1件以上書いてください。")
    for index, note in enumerate(notes, start=1):
        if not isinstance(note, str) or not note.strip():
            fail(f"site.notes の {index} 件目が空です。")
    seen: set[int] = set()
    prepared: list[dict] = []
    for episode in episodes:
        if not isinstance(episode, dict):
            fail("episodes の各要素はオブジェクトにしてください。")
        number = episode.get("number")
        if not isinstance(number, int) or isinstance(number, bool) or number < 1:
            fail(f"number は 1 以上の整数にしてください: {number!r}")
        where = f"第{number}回"
        if number in seen:
            fail(f"{where} の number が重複しています。")
        seen.add(number)
        title = require_str(episode, "title", where)
        if title.startswith("第"):
            fail(f"{where} の title に「第N回」は含めないでください。番号は number から付きます。")
        date = require_str(episode, "date", where)
        image_name = require_str(episode, "image", where)
        if not IMAGE_RE.fullmatch(image_name):
            fail(
                f"{where} の image は半角英数字とハイフンだけの .jpg にしてください"
                f"（例: 05-example.jpg）: {image_name}"
            )
        image_path = (IMAGES / image_name).resolve()
        try:
            image_path.relative_to(IMAGES.resolve())
        except ValueError:
            fail(f"{where} の画像パスが images/ の外を指しています。")
        if not image_path.is_file():
            fail(f"{where} の画像が見つかりません: images/{image_name}")
        width, height = jpeg_size(image_path)
        if width > FULL_MAX_WIDTH:
            fail(
                f"{where} の画像が広すぎます（{width}px）。次でおよそ1200pxにしてから置いてください。\n"
                f"python3 scripts/optimize_image.py 元画像.jpg images/{image_name}"
            )
        source = require_str(episode, "source", where)
        image_alt = require_str(episode, "imageAlt", where)
        daily = require_str(episode, "daily", where)
        blocks = episode.get("blocks")
        if not isinstance(blocks, list) or not blocks:
            fail(f"{where} の blocks に、段落と引用を1件以上書いてください。")
        clean_blocks: list[dict] = []
        for block_index, block in enumerate(blocks, start=1):
            if not isinstance(block, dict):
                fail(f"{where} の blocks {block_index} 件目がオブジェクトではありません。")
            block_type = block.get("type")
            text = require_str(block, "text", f"{where} の blocks {block_index} 件目")
            if block_type == "paragraph":
                clean_blocks.append({"type": "paragraph", "text": text})
            elif block_type == "quote":
                quote_source = block.get("source")
                if not isinstance(quote_source, str) or not quote_source.strip():
                    fail(
                        f"{where} の引用（{block_index}件目）に source がありません。"
                        "引用のすぐ横に出典を出すため、source は必須です。"
                    )
                clean_blocks.append({"type": "quote", "text": text, "source": quote_source.strip()})
            else:
                fail(f"{where} の blocks {block_index} 件目の type は paragraph か quote です。")
        thumb_path = THUMBS / image_name
        thumb_width, thumb_height = make_thumb(image_path, thumb_path)
        prepared.append(
            {
                "number": number,
                "title": title,
                "date": date,
                "iso": iso_date(date, where),
                "image": image_name,
                "image_alt": image_alt,
                "source": source,
                "daily": daily,
                "blocks": clean_blocks,
                "width": width,
                "height": height,
                "thumb_width": thumb_width,
                "thumb_height": thumb_height,
                "page": f"episodes/{number:03d}.html",
            }
        )
    ordered = sorted(prepared, key=lambda item: item["number"])
    for index, episode in enumerate(ordered):
        episode["prev"] = ordered[index - 1] if index else None
        episode["next"] = ordered[index + 1] if index + 1 < len(ordered) else None
    site = {
        "title": site["title"].strip(),
        "url": url.rstrip("/"),
        "notes": [note.strip() for note in notes],
    }
    return site, ordered


def render_notes(notes: list[str]) -> str:
    items = "\n".join(f"      <li>{esc(note)}</li>" for note in notes)
    return f"""    <footer class="site-footer" id="notes">
      <div class="wrap">
        <h2>注記</h2>
        <ul>
{items}
        </ul>
      </div>
    </footer>"""


def render_header(site_title: str, prefix: str, home: bool) -> str:
    title = esc(site_title)
    if home:
        heading = f'<h1 class="site-title">{title}</h1>'
    else:
        heading = f'<p class="site-title"><a href="{prefix}index.html">{title}</a></p>'
    return f"""    <header class="site-header">
      <div class="wrap">
        {heading}
        <p class="header-note"><a href="#notes">注記</a></p>
        <div class="rule" aria-hidden="true"><span></span></div>
      </div>
    </header>"""


def render_head(
    site: dict,
    prefix: str,
    title: str,
    description: str,
    canonical_path: str,
    og_type: str,
    image: str | None = None,
    image_width: int | None = None,
    image_height: int | None = None,
    preload: str | None = None,
    prev_href: str | None = None,
    next_href: str | None = None,
) -> str:
    canonical = f"{site['url']}/{canonical_path}" if canonical_path else f"{site['url']}/"
    lines = [
        "<!DOCTYPE html>",
        '<html lang="ja">',
        "<head>",
        '  <meta charset="utf-8">',
        '  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">',
        f"  <title>{esc(title)}</title>",
        f'  <meta name="description" content="{esc(description)}">',
        '  <meta name="theme-color" content="#f3ecdf">',
        '  <meta name="format-detection" content="telephone=no">',
        f'  <link rel="canonical" href="{esc(canonical)}">',
        f'  <link rel="icon" href="{prefix}favicon.svg" type="image/svg+xml">',
        f'  <link rel="stylesheet" href="{prefix}css/style.css">',
        "  " + FONT_LINKS.replace("\n", "\n  "),
        '  <meta property="og:locale" content="ja_JP">',
        f'  <meta property="og:type" content="{esc(og_type)}">',
        f'  <meta property="og:site_name" content="{esc(site["title"])}">',
        f'  <meta property="og:title" content="{esc(title)}">',
        f'  <meta property="og:description" content="{esc(description)}">',
        f'  <meta property="og:url" content="{esc(canonical)}">',
        '  <meta name="twitter:card" content="summary_large_image">',
    ]
    if image:
        image_url = f"{site['url']}/{image}"
        lines.append(f'  <meta property="og:image" content="{esc(image_url)}">')
        if image_width and image_height:
            lines.append(f'  <meta property="og:image:width" content="{image_width}">')
            lines.append(f'  <meta property="og:image:height" content="{image_height}">')
    if preload:
        lines.append(f'  <link rel="preload" as="image" href="{esc(preload)}">')
    if prev_href:
        lines.append(f'  <link rel="prev" href="{esc(prev_href)}">')
    if next_href:
        lines.append(f'  <link rel="next" href="{esc(next_href)}">')
    lines.append("</head>")
    return "\n".join(lines)


def title_html(title: str) -> str:
    """読みがなの括弧内では改行しない。文字そのものは変えない。"""
    return re.sub(r"（[^）]*）", lambda match: f'<span class="title-kana">{match.group(0)}</span>', esc(title))


def render_blocks(blocks: list[dict]) -> str:
    parts: list[str] = []
    for block in blocks:
        if block["type"] == "paragraph":
            parts.append(f"        <p>{esc(block['text'])}</p>")
            continue
        parts.append(
            "\n".join(
                [
                    "        <blockquote>",
                    "          <p>"
                    f"{esc(block['text'])} "
                    "<span class=\"quote-source\"><span class=\"source-label\">出典</span> "
                    f"<cite>{esc(block['source'])}</cite></span></p>",
                    "        </blockquote>",
                ]
            )
        )
    return "\n".join(parts)


def render_pager(episode: dict) -> str:
    previous = episode["prev"]
    following = episode["next"]
    if not previous and not following:
        return ""
    chunks: list[str] = ['      <nav class="pager" aria-label="前後の法話">']
    if previous:
        chunks.append(
            "\n".join(
                [
                    f'        <a class="prev" href="{previous["number"]:03d}.html" rel="prev">',
                    '          <span class="pager-label">前の法話</span>',
                    f'          <span class="pager-title">第{previous["number"]}回 {title_html(previous["title"])}</span>',
                    f'          <span class="pager-date"><time datetime="{previous["iso"]}">{esc(previous["date"])}</time></span>',
                    "        </a>",
                ]
            )
        )
    if following:
        chunks.append(
            "\n".join(
                [
                    f'        <a class="next" href="{following["number"]:03d}.html" rel="next">',
                    '          <span class="pager-label">次の法話</span>',
                    f'          <span class="pager-title">第{following["number"]}回 {title_html(following["title"])}</span>',
                    f'          <span class="pager-date"><time datetime="{following["iso"]}">{esc(following["date"])}</time></span>',
                    "        </a>",
                ]
            )
        )
    chunks.append("      </nav>")
    return "\n".join(chunks)


def render_episode(site: dict, episode: dict) -> str:
    prefix = "../"
    full_title = f"第{episode['number']}回 {episode['title']}"
    document_title = f"{full_title}｜{site['title']}"
    image_src = f"../images/{episode['image']}"
    previous = episode["prev"]
    following = episode["next"]
    head = render_head(
        site,
        prefix,
        document_title,
        episode["daily"],
        episode["page"],
        "article",
        image=f"images/{episode['image']}",
        image_width=episode["width"],
        image_height=episode["height"],
        preload=image_src,
        prev_href=f"{previous['number']:03d}.html" if previous else None,
        next_href=f"{following['number']:03d}.html" if following else None,
    )
    return f"""{head}
<body>
  <!-- data/episodes.json から scripts/build.py が生成しました。手で編集しないでください。 -->
  <a class="skip" href="#main">本文へスキップ</a>
{render_header(site["title"], prefix, home=False)}
  <main id="main">
    <article class="episode">
      <div class="wrap">
        <h1 class="episode-title"><span class="episode-number">第{episode["number"]}回</span>{title_html(episode["title"])}</h1>
        <p class="episode-date"><span class="label">配信日</span><time datetime="{episode["iso"]}">{esc(episode["date"])}</time></p>
        <p class="episode-source"><span class="source-label">出典</span><span class="source-text">{esc(episode["source"])}</span></p>
        <figure class="hero-figure">
          <img src="{image_src}" width="{episode["width"]}" height="{episode["height"]}" alt="{esc(episode["image_alt"])}" fetchpriority="high" decoding="async">
        </figure>
        <div class="talk">
{render_blocks(episode["blocks"])}
        </div>
        <aside class="daily">
          <h2>暮らしのひとこと</h2>
          <p>{esc(episode["daily"])}</p>
        </aside>
{render_pager(episode)}
        <p class="back"><a href="../index.html">法話の一覧へ</a></p>
      </div>
    </article>
  </main>
{render_notes(site["notes"])}
</body>
</html>
"""


def render_index(site: dict, episodes: list[dict]) -> str:
    newest_first = list(reversed(episodes))
    description = newest_first[0]["daily"] if newest_first else site["title"]
    image = None
    image_width = None
    image_height = None
    if newest_first:
        image = f"images/{newest_first[0]['image']}"
        image_width = newest_first[0]["width"]
        image_height = newest_first[0]["height"]
    head = render_head(
        site,
        "",
        site["title"],
        description,
        "",
        "website",
        image=image,
        image_width=image_width,
        image_height=image_height,
        preload=image,
    )
    if not newest_first:
        listing = '      <p class="empty">まだ法話がありません。</p>'
    else:
        cards: list[str] = []
        for index, episode in enumerate(newest_first):
            latest = index == 0
            if latest:
                src = f"images/{episode['image']}"
                width, height = episode["width"], episode["height"]
                loading = 'fetchpriority="high" '
                alt = esc(episode["image_alt"])
            else:
                src = f"images/thumbs/{episode['image']}"
                width, height = episode["thumb_width"], episode["thumb_height"]
                loading = 'loading="lazy" '
                alt = ""
            daily = ""
            if latest:
                daily = (
                    '\n          <p class="card-daily"><span class="label">暮らしのひとこと</span>'
                    f"{esc(episode['daily'])}</p>"
                )
            cards.append(
                "\n".join(
                    [
                        f'        <li class="episode-card{" is-latest" if latest else ""}">',
                        f'          <a href="{episode["page"]}">',
                        '            <div class="thumb">',
                        f'              <img src="{src}" width="{width}" height="{height}" alt="{alt}" {loading}decoding="async">',
                        "            </div>",
                        '            <div class="card-body">',
                        f'              <p class="card-kicker">第{episode["number"]}回 <time datetime="{episode["iso"]}">{esc(episode["date"])}</time></p>',
                        f"              <h2>{esc(episode['title'])}</h2>{daily}",
                        "            </div>",
                        "          </a>",
                        "        </li>",
                    ]
                )
            )
        listing = "      <ol class=\"episode-list\">\n" + "\n".join(cards) + "\n      </ol>"
    return f"""{head}
<body>
  <!-- data/episodes.json から scripts/build.py が生成しました。手で編集しないでください。 -->
  <a class="skip" href="#main">本文へスキップ</a>
{render_header(site["title"], "", home=True)}
  <main id="main">
    <div class="wrap">
      <p class="list-note">新しい回から並んでいます。</p>
{listing}
    </div>
  </main>
{render_notes(site["notes"])}
</body>
</html>
"""


def render_404(site: dict) -> str:
    head = render_head(site, "", f"ページが見つかりません｜{site['title']}", site["title"], "404.html", "website")
    return f"""{head}
<body>
  <a class="skip" href="#main">本文へスキップ</a>
{render_header(site["title"], "", home=False)}
  <main id="main">
    <div class="wrap prose">
      <h1>ページが見つかりません</h1>
      <p>アドレスをご確認いただくか、法話の一覧からお探しください。</p>
      <p class="back"><a href="index.html">法話の一覧へ</a></p>
    </div>
  </main>
{render_notes(site["notes"])}
</body>
</html>
"""


def assert_contains(page: str, text: str, label: str) -> None:
    if esc(text) not in page:
        fail(f"生成結果に載っていません（{label}）: {text[:48]}")


def verify(site: dict, episodes: list[dict], index_html: str, pages: dict[int, str]) -> None:
    assert_contains(index_html, site["title"], "一覧の題")
    for note in site["notes"]:
        assert_contains(index_html, note, "一覧の注記")
    positions: list[int] = []
    for episode in sorted(episodes, key=lambda item: item["number"], reverse=True):
        href = episode["page"]
        position = index_html.find(href)
        if position < 0:
            fail(f"一覧にリンクがありません: {href}")
        positions.append(position)
        assert_contains(index_html, episode["title"], "一覧の題名")
    if positions != sorted(positions):
        fail("一覧が新しい順になっていません。")
    for episode in episodes:
        page = pages[episode["number"]]
        assert_contains(page, episode["title"], f"第{episode['number']}回の題")
        assert_contains(page, episode["date"], f"第{episode['number']}回の配信日")
        assert_contains(page, "配信日", f"第{episode['number']}回の配信日ラベル")
        assert_contains(page, episode["source"], f"第{episode['number']}回の出典")
        assert_contains(page, episode["daily"], f"第{episode['number']}回の暮らしのひとこと")
        assert_contains(page, "暮らしのひとこと", f"第{episode['number']}回の暮らしの見出し")
        for note in site["notes"]:
            assert_contains(page, note, f"第{episode['number']}回の注記")
        talk = page.split('class="talk"', 1)[1].split('class="daily"', 1)[0]
        header = page.split('class="talk"', 1)[0]
        if "episode-source" not in header or esc(episode["source"]) not in header:
            fail(f"第{episode['number']}回の出典が、本文の前の出典欄にありません。")
        for block in episode["blocks"]:
            if esc(block["text"]) not in talk:
                fail(f"第{episode['number']}回の本文が見つかりません: {block['text'][:32]}")
            if block["type"] == "quote":
                if esc(block["source"]) not in talk:
                    fail(f"第{episode['number']}回の引用の出典が本文中にありません。")
                quote_at = talk.find(esc(block["text"]))
                source_at = talk.find(esc(block["source"]), quote_at)
                if source_at < 0 or source_at - quote_at > 800:
                    fail(f"第{episode['number']}回の引用と出典が離れています。")
        if episode["prev"] and f'{episode["prev"]["number"]:03d}.html' not in page:
            fail(f"第{episode['number']}回に前の法話へのリンクがありません。")
        if episode["next"] and f'{episode["next"]["number"]:03d}.html' not in page:
            fail(f"第{episode['number']}回に次の法話へのリンクがありません。")
        if episode["prev"] is None and 'class="prev"' in page:
            fail(f"第{episode['number']}回は最初の回なので、前の法話は不要です。")
        if episode["next"] is None and 'class="next"' in page:
            fail(f"第{episode['number']}回は最新なので、次の法話は不要です。")


def main() -> None:
    site, episodes = validate(load_data())
    index_html = render_index(site, episodes)
    pages = {episode["number"]: render_episode(site, episode) for episode in episodes}
    not_found = render_404(site)
    verify(site, episodes, index_html, pages)
    (ROOT / "index.html").write_text(index_html, encoding="utf-8")
    (ROOT / "404.html").write_text(not_found, encoding="utf-8")
    episode_dir = ROOT / "episodes"
    episode_dir.mkdir(exist_ok=True)
    expected = {f"{episode['number']:03d}.html" for episode in episodes}
    for stale in episode_dir.glob("*.html"):
        if stale.name not in expected:
            stale.unlink()
            print(f"削除しました: episodes/{stale.name}")
    for episode in episodes:
        (episode_dir / f"{episode['number']:03d}.html").write_text(pages[episode["number"]], encoding="utf-8")
    print("生成しました。")
    print("  index.html")
    print("  404.html")
    for episode in sorted(episodes, key=lambda item: item["number"], reverse=True):
        print(f"  {episode['page']}  第{episode['number']}回 {episode['title']}")
    if episodes:
        order = "、".join(f"第{episode['number']}回" for episode in reversed(episodes))
        print(f"一覧の並び（新しい順）: {order}")


if __name__ == "__main__":
    main()
