"""
Frontend serving endpoint.

This module serves the chat interface HTML page.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["frontend"])
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def chat_interface(request: Request):
    """
    Serve the main chat interface page.
    
    Args:
        request: FastAPI request object
        
    Returns:
        HTMLResponse: The rendered chat interface
    """
    return templates.TemplateResponse("index.html", {"request": request})

# Made with Bob
