"""
GW2 CounterPicker - Night Intelligence Report PDF Generator
Creates beautiful PDF reports for sharing with your guild
"""

import os
from datetime import datetime
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from models import EveningReport, CounterRecommendation


# Ensure reports directory exists
REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(exist_ok=True)


def generate_night_report_pdf(report: EveningReport, counter: CounterRecommendation) -> str:
    """Generate a beautiful Night Intelligence Report PDF"""
    
    filename = REPORTS_DIR / f"night_report_{report.session_id[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    doc = SimpleDocTemplate(
        str(filename),
        pagesize=A4,
        rightMargin=1.5*cm,
        leftMargin=1.5*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    # Custom styles
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=28,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#8B5CF6')
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=20,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#6366F1')
    )
    
    section_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=16,
        spaceBefore=20,
        spaceAfter=10,
        textColor=colors.HexColor('#8B5CF6')
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=8,
        textColor=colors.HexColor('#333333')
    )
    
    insight_style = ParagraphStyle(
        'Insight',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=6,
        leftIndent=20,
        textColor=colors.HexColor('#4B5563')
    )
    
    # Build document content
    content = []
    
    # Title
    content.append(Paragraph("🔮 NIGHT INTELLIGENCE REPORT", title_style))
    content.append(Paragraph(
        f"Generated: {report.created_at.strftime('%Y-%m-%d %H:%M')} | Session: {report.session_id[:8]}",
        subtitle_style
    ))
    
    content.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#8B5CF6')))
    content.append(Spacer(1, 20))
    
    # Overview Section
    content.append(Paragraph("📊 OVERVIEW", section_style))
    
    overview_data = [
        ["Enemy Server", report.enemy_server],
        ["Total Fights", str(report.total_fights)],
        ["Duration", f"{report.total_duration_minutes} minutes"],
        ["Files Analyzed", str(report.total_files_analyzed)],
        ["Enemy Comp Type", report.average_composition.estimated_squad_type],
    ]
    
    overview_table = Table(overview_data, colWidths=[3*inch, 4*inch])
    overview_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F3F4F6')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1F2937')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
    ]))
    content.append(overview_table)
    content.append(Spacer(1, 20))
    
    # Key Insights
    content.append(Paragraph("💡 KEY INSIGHTS", section_style))
    for insight in report.key_insights:
        content.append(Paragraph(insight, insight_style))
    content.append(Spacer(1, 20))
    
    # Enemy Composition
    content.append(Paragraph("⚔️ ENEMY COMPOSITION ANALYSIS", section_style))
    
    comp_data = [["Elite Spec", "Count", "Role"]]
    for spec, count in sorted(report.average_composition.spec_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        role = "Unknown"
        # Try to determine role from builds
        for build in report.average_composition.builds:
            if build.elite_spec == spec:
                role = build.role
                break
        comp_data.append([spec, str(count), role])
    
    comp_table = Table(comp_data, colWidths=[2.5*inch, 1.5*inch, 2*inch])
    comp_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#8B5CF6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9FAFB')]),
    ]))
    content.append(comp_table)
    content.append(Spacer(1, 20))
    
    # Top Players
    content.append(Paragraph("🎯 TOP 10 THREATS", section_style))
    
    players_data = [["Rank", "Player", "Spec", "Times Seen", "Avg Damage", "Threat"]]
    for player in report.top_players:
        players_data.append([
            f"#{player.rank}",
            player.player_name[:15],
            player.elite_spec,
            str(player.times_seen),
            f"{player.avg_damage:,}",
            player.threat_level
        ])
    
    players_table = Table(players_data, colWidths=[0.6*inch, 1.5*inch, 1.2*inch, 1*inch, 1.2*inch, 0.8*inch])
    players_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6366F1')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9FAFB')]),
    ]))
    content.append(players_table)
    
    # Page break before recommendations
    content.append(PageBreak())
    
    # Counter Recommendations
    content.append(Paragraph("🛡️ RECOMMENDED COUNTER COMPOSITION", section_style))
    content.append(Paragraph(
        f"Confidence Score: {counter.confidence_score:.0f}%",
        body_style
    ))
    content.append(Spacer(1, 10))
    
    counter_data = [["Priority", "Spec", "Role", "Reason"]]
    for build in counter.recommended_builds[:6]:
        priority_stars = "⭐" * build.priority
        counter_data.append([
            priority_stars,
            build.elite_spec,
            build.role,
            build.reason[:40] + "..." if len(build.reason) > 40 else build.reason
        ])
    
    counter_table = Table(counter_data, colWidths=[1*inch, 1.3*inch, 1*inch, 3*inch])
    counter_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#10B981')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F0FDF4')]),
    ]))
    content.append(counter_table)
    content.append(Spacer(1, 20))
    
    # Strategy Notes
    content.append(Paragraph("📋 STRATEGY NOTES", section_style))
    for note in counter.strategy_notes:
        content.append(Paragraph(note, insight_style))
    content.append(Spacer(1, 15))
    
    # Key Targets
    content.append(Paragraph("🎯 Priority Targets:", body_style))
    for target in counter.key_targets:
        content.append(Paragraph(f"  • {target}", insight_style))
    content.append(Spacer(1, 10))
    
    # Avoid List
    content.append(Paragraph("⚠️ Avoid:", body_style))
    for avoid in counter.avoid_list:
        content.append(Paragraph(f"  • {avoid}", insight_style))
    content.append(Spacer(1, 20))
    
    # Heatmap Data (text version)
    content.append(Paragraph("🗺️ CONTESTED ZONES", section_style))
    
    zone_data = [["Zone", "Fights", "Total Kills", "Intensity"]]
    for zone in report.heatmap_zones[:8]:
        intensity_bar = "█" * int(zone.intensity * 10)
        zone_data.append([
            zone.zone_name,
            str(zone.fight_count),
            str(zone.total_kills),
            intensity_bar
        ])
    
    zone_table = Table(zone_data, colWidths=[2.5*inch, 1*inch, 1.2*inch, 1.5*inch])
    zone_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F59E0B')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
    ]))
    content.append(zone_table)
    content.append(Spacer(1, 30))
    
    # Footer
    content.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#8B5CF6')))
    content.append(Spacer(1, 10))
    
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=9,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#6B7280')
    )
    content.append(Paragraph(
        "Generated by GW2 CounterPicker | The Ultimate WvW Intelligence Tool",
        footer_style
    ))
    content.append(Paragraph(
        "\"Le seul outil capable de lire dans l'âme de ton adversaire.\"",
        footer_style
    ))
    content.append(Paragraph(
        "Made with rage, love and 15 years of WvW pain.",
        footer_style
    ))
    
    # Build PDF
    doc.build(content)
    
    return str(filename)
