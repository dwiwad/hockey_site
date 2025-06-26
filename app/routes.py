from fastapi import APIRouter

router = APIRouter()

@router.get("/blog")
def read_blog():
    return {"title": "First Blog Post", "content": "This is the body of the post."}

@router.get("/about")
def about_page():
    return {"about": "This is an about page."}
