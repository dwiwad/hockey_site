import markdown
import frontmatter
import os

def load_deep_dive(slug: str):
    path = f"posts/{slug}.md"
    if not os.path.isfile(path):
        return None

    with open(path, "r", encoding="utf-8") as f:
        post = frontmatter.load(f)

    html_content = markdown.markdown(
        post.content,
        extensions=["fenced_code", "tables", "toc"]
    )

    return {
        "title": post.get("title", "Untitled"),
        "date": post.get("date", ""),
        "image": post.get("image", ""),
        "content": html_content,
        "data_source": post.get("data_source", None),
    }
