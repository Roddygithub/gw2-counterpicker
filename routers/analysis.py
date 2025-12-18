"""
Analysis router - File upload and analysis endpoints
"""

from fastapi import APIRouter, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import List
from datetime import datetime
import httpx

from rate_limiter import check_upload_rate_limit
from services.file_validator import validate_upload_file
from services.analysis_service import (
    analyze_single_file,
    analyze_multiple_files,
    analyze_dps_report_url
)
from services.counter_service import get_counter_service
from logger import get_logger

router = APIRouter(prefix="/api/analyze")
templates = Jinja2Templates(directory="templates")
logger = get_logger('analysis_router')


def get_lang(request: Request) -> str:
    """Get language from cookie or default to French"""
    return request.cookies.get("lang", "fr")


@router.post("/url")
async def analyze_url(request: Request, url: str = Form(...)):
    """
    Analyze a single dps.report URL
    """
    lang = get_lang(request)
    
    try:
        result = await analyze_dps_report_url(url, lang)
        result["request"] = request
        return templates.TemplateResponse("partials/dps_report_result.html", result)
    except Exception as e:
        logger.error(f"dps.report API failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch dps.report data")


@router.post("/evtc")
async def analyze_evtc(
    request: Request,
    files: List[UploadFile] = File(...)
):
    """
    Unified endpoint: Analyze single or multiple .evtc files
    Strategy: Try dps.report first, fallback to local parser if unavailable
    
    Security: Rate limited to 10 uploads/min, max 50MB per file, ZIP validation
    """
    # Rate limiting check
    await check_upload_rate_limit(request)
    
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    lang = get_lang(request)
    
    # Single file mode
    if len(files) == 1:
        file = files[0]
        
        # Validate and read file securely
        data = await validate_upload_file(file)
        logger.info(f"Received file: {file.filename}, size: {len(data)} bytes")
        
        result = await analyze_single_file(file.filename, data, file.size, lang)
        result["request"] = request
        return templates.TemplateResponse("partials/dps_report_result.html", result)
    
    # Multiple files mode
    else:
        # Validate all files
        validated_files = []
        for file in files:
            try:
                content = await validate_upload_file(file)
                validated_files.append((file.filename, content))
            except HTTPException as e:
                raise HTTPException(
                    status_code=e.status_code,
                    detail=f"File '{file.filename}': {e.detail}"
                )
        
        result = await analyze_multiple_files(validated_files, lang)
        result["request"] = request
        return templates.TemplateResponse("partials/multi_result.html", result)




@router.post("/confirm-result")
async def confirm_result(request: Request):
    body = await request.json()
    worked = bool(body.get("worked"))
    enemy_comp = body.get("enemy_comp", {})
    context = body.get("context", "zerg")
    try:
        get_counter_service().record_feedback(enemy_comp, worked, context)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"confirm_result failed: {e}")
        return {"status": "error"}
