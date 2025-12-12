"""
GW2 CounterPicker - The Ultimate WvW Intelligence Tool
"Le seul outil capable de lire dans l'âme de ton adversaire. Et dans celle de tout son serveur."

Made with rage, love and 15 years of WvW pain.
"""

import os
import uuid
import json
import random
from datetime import datetime, timedelta
from typing import Optional, List
from pathlib import Path

from fastapi import FastAPI, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import httpx

from models import (
    AnalysisResult, PlayerBuild, CompositionAnalysis, 
    CounterRecommendation, EveningReport, HourlyEvolution,
    HeatmapData, TopPlayer
)
from mock_parser import MockEVTCParser
from counter_engine import CounterPickEngine

app = FastAPI(
    title="GW2 CounterPicker",
    description="The most powerful WvW intelligence tool ever created",
    version="1.0.0"
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Initialize engines
parser = MockEVTCParser()
counter_engine = CounterPickEngine()

# Store for analysis sessions
sessions = {}


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Main landing page - The gateway to victory"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "title": "GW2 CounterPicker"
    })


@app.get("/analyze", response_class=HTMLResponse)
async def analyze_page(request: Request):
    """Single report analysis page"""
    return templates.TemplateResponse("analyze.html", {
        "request": request,
        "title": "Quick Analysis"
    })


@app.get("/evening", response_class=HTMLResponse)
async def evening_page(request: Request):
    """Full evening analysis page"""
    return templates.TemplateResponse("evening.html", {
        "request": request,
        "title": "Soirée Complète"
    })


@app.get("/meta", response_class=HTMLResponse)
async def meta_page(request: Request):
    """Meta 2025 page - Current trending builds"""
    meta_data = counter_engine.get_current_meta()
    return templates.TemplateResponse("meta.html", {
        "request": request,
        "title": "Meta 2025",
        "meta_data": meta_data
    })


@app.post("/api/analyze/url")
async def analyze_dps_report(request: Request, url: str = Form(...)):
    """
    Analyze a single dps.report URL
    Returns enemy composition and perfect counter in 3 seconds
    """
    # Validate URL
    if not url or "dps.report" not in url:
        raise HTTPException(status_code=400, detail="Invalid dps.report URL")
    
    # Parse the report (mocked for now)
    analysis = parser.parse_dps_report_url(url)
    
    # Generate counter recommendations
    counter = counter_engine.generate_counter(analysis.enemy_composition)
    
    # Return HTML partial for HTMX
    return templates.TemplateResponse("partials/analysis_result.html", {
        "request": request,
        "analysis": analysis,
        "counter": counter,
        "timestamp": datetime.now().strftime("%H:%M:%S")
    })


@app.post("/api/analyze/files")
async def analyze_evening_files(
    request: Request,
    files: List[UploadFile] = File(...)
):
    """
    Analyze multiple .evtc/.zip files for full evening analysis
    Returns comprehensive intelligence report
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")
    
    if len(files) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 files allowed")
    
    # Create session
    session_id = str(uuid.uuid4())
    
    # Process all files (mocked)
    file_infos = []
    for f in files:
        file_infos.append({
            "filename": f.filename,
            "size": f.size or 0
        })
    
    # Generate comprehensive evening report
    report = parser.parse_evening_files(file_infos)
    
    # Generate counter for next evening
    counter = counter_engine.generate_counter(report.average_composition)
    
    # Store session
    sessions[session_id] = {
        "report": report,
        "counter": counter,
        "created_at": datetime.now()
    }
    
    return templates.TemplateResponse("partials/evening_result.html", {
        "request": request,
        "report": report,
        "counter": counter,
        "session_id": session_id,
        "file_count": len(files)
    })


@app.get("/api/report/{session_id}/pdf")
async def download_pdf_report(session_id: str):
    """Download Night Intelligence Report as PDF"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    
    # Generate PDF (simplified for now)
    from pdf_generator import generate_night_report_pdf
    
    pdf_path = generate_night_report_pdf(session["report"], session["counter"])
    
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"night_intelligence_report_{session_id[:8]}.pdf"
    )


@app.get("/api/share/{session_id}")
async def get_shared_report(request: Request, session_id: str):
    """View a shared evening report"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Report not found")
    
    session = sessions[session_id]
    
    return templates.TemplateResponse("shared_report.html", {
        "request": request,
        "report": session["report"],
        "counter": session["counter"],
        "session_id": session_id
    })


@app.get("/health")
async def health_check():
    """Health check endpoint for deployment"""
    return {"status": "operational", "message": "GW2 CounterPicker is ready for war"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
