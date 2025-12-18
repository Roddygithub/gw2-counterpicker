"""
Pages router - Main website pages (home, about, analyze, meta)
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from services.counter_service import get_counter_service
from translations import get_all_translations

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def get_lang(request: Request) -> str:
    """Get language from cookie or default to French"""
    return request.cookies.get("lang", "fr")


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Main landing page - The gateway to victory"""
    lang = get_lang(request)
    stats_status = get_counter_service().get_status()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "title": "GW2 CounterPicker",
        "lang": lang,
        "t": get_all_translations(lang),
        "ai_status": stats_status
    })


@router.get("/set-lang/{lang}")
async def set_language(request: Request, lang: str):
    """Set user language preference"""
    if lang not in ["fr", "en"]:
        lang = "fr"
    response = RedirectResponse(url=request.headers.get("referer", "/"), status_code=302)
    response.set_cookie(key="lang", value=lang, max_age=365*24*60*60)
    return response


@router.get("/about", response_class=HTMLResponse)
async def about_page(request: Request):
    """About page - How it works and limitations"""
    lang = get_lang(request)
    return templates.TemplateResponse("about.html", {
        "request": request,
        "title": "About" if lang == 'en' else "À propos",
        "lang": lang,
        "t": get_all_translations(lang)
    })


@router.get("/analyze", response_class=HTMLResponse)
async def analyze_page(request: Request):
    """Unified analysis page - Single or multiple files"""
    lang = get_lang(request)
    return templates.TemplateResponse("analyze.html", {
        "request": request,
        "title": "Analyze" if lang == 'en' else "Analyser",
        "lang": lang,
        "t": get_all_translations(lang)
    })


@router.get("/evening", response_class=HTMLResponse)
async def evening_page_redirect(request: Request):
    """Redirect old /evening route to /analyze"""
    return RedirectResponse(url="/analyze", status_code=301)


@router.get("/meta", response_class=HTMLResponse)
async def meta_page(request: Request):
    """Meta analysis page - Current WvW meta trends"""
    return RedirectResponse(url="/meta/zerg", status_code=302)
