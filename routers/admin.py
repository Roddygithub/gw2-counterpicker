from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates

from services.counter_service import get_counter_service
from translations import get_all_translations

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory="templates")


def get_lang(request: Request) -> str:
    return request.cookies.get("lang", "fr")


@router.get("/feedback", response_class=HTMLResponse)
async def feedback_page(request: Request):
    lang = get_lang(request)
    summary = get_counter_service().get_feedback_summary()
    settings = get_counter_service().get_settings()
    return templates.TemplateResponse("admin/feedback.html", {
        "request": request,
        "title": "Admin Feedback",
        "lang": lang,
        "t": get_all_translations(lang),
        "summary": summary,
        "settings": settings,
    })


@router.post("/feedback/settings")
async def feedback_settings(request: Request, feedback_weight: float = Form(...)):
    get_counter_service().update_settings({"feedback_weight": float(feedback_weight)})
    return await feedback_page(request)


@router.get("/feedback/export.csv")
async def feedback_export_csv(request: Request):
    import csv
    import io
    summary = get_counter_service().get_feedback_summary()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["enemy_comp_hash", "total", "worked", "success_rate", "contexts_json"])
    for row in summary.get("by_comp", []):
        writer.writerow([
            row.get("enemy_comp_hash"),
            row.get("total"),
            row.get("worked"),
            row.get("success_rate"),
            str(row.get("contexts", {}))
        ])
    data = output.getvalue()
    return Response(content=data, media_type="text/csv")
