import os
from pathlib import Path
from datetime import datetime, date
import markdown
import frontmatter

# Resolve project root based on THIS file’s location
BASE_DIR = Path(__file__).resolve().parents[2]  # adjust depth if your tree differs
POSTS_DIR = BASE_DIR / "posts"

def _coerce_datetime(d):
    if isinstance(d, datetime):
        return d
    if isinstance(d, date):
        return datetime(d.year, d.month, d.day)
    if isinstance(d, str) and d.strip():
        # Try common formats first
        for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(d, fmt)
            except ValueError:
                pass
        # ISO fallback
        try:
            return datetime.fromisoformat(d)
        except Exception:
            pass
    # Fallback: far past date so it sorts last
    return datetime(1900, 1, 1)

def _load_post_from_path(path: Path, slug: str):
    with path.open("r", encoding="utf-8") as f:
        post = frontmatter.load(f)

    post_dt = _coerce_datetime(post.get("date", ""))

    html_content = markdown.markdown(
        post.content,
        extensions=["fenced_code", "tables", "toc"]
    )

    return {
        "slug": slug,
        "title": post.get("title", "Untitled"),
        "short_title": post.get("short_title"),
        "date": post_dt,                               # datetime for sorting
        "date_str": post_dt.strftime("%B %d, %Y"),     # safe string for templates
        "image": post.get("image", ""),
        "tag": post.get("tag", "Deep Dive"),
        "summary": post.get("summary", ""),
        "description": post.get("description", ""),
        "keywords": post.get("keywords", ""),
        "content": html_content,
        "data_source": post.get("data_source", None),
    }

def load_deep_dive(slug: str):
    path = POSTS_DIR / f"{slug}.md"
    if not path.is_file():
        return None
    return _load_post_from_path(path, slug)

def load_all_deep_dives():
    if not POSTS_DIR.exists():
        # Empty list if posts folder missing (prevents 500)
        return []

    posts = []
    for filename in os.listdir(POSTS_DIR):
        if not filename.endswith(".md"):
            continue
        slug = filename[:-3]
        path = POSTS_DIR / filename
        try:
            posts.append(_load_post_from_path(path, slug))
        except Exception:
            # Skip unreadable/malformed files instead of crashing
            continue

    posts.sort(key=lambda p: p["date"], reverse=True)
    return posts
