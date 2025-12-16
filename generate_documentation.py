#!/usr/bin/env python3
"""
GW2 CounterPicker - Documentation Generator
Generates a comprehensive PDF documentation of the entire project
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, 
    PageBreak, ListFlowable, ListItem, Image
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from datetime import datetime

# Colors
PURPLE = colors.HexColor('#8B5CF6')
DARK_PURPLE = colors.HexColor('#6D28D9')
PINK = colors.HexColor('#EC4899')
DARK_BG = colors.HexColor('#0F0A1F')
GRAY = colors.HexColor('#6B7280')

def create_styles():
    """Create custom styles for the document"""
    styles = getSampleStyleSheet()
    
    # Title style
    styles.add(ParagraphStyle(
        name='DocTitle',
        parent=styles['Title'],
        fontSize=28,
        textColor=PURPLE,
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    ))
    
    # Subtitle
    styles.add(ParagraphStyle(
        name='DocSubtitle',
        parent=styles['Normal'],
        fontSize=14,
        textColor=GRAY,
        spaceAfter=20,
        alignment=TA_CENTER
    ))
    
    # Section header
    styles.add(ParagraphStyle(
        name='SectionHeader',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=DARK_PURPLE,
        spaceBefore=20,
        spaceAfter=12,
        fontName='Helvetica-Bold'
    ))
    
    # Subsection header
    styles.add(ParagraphStyle(
        name='SubsectionHeader',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=PURPLE,
        spaceBefore=15,
        spaceAfter=8,
        fontName='Helvetica-Bold'
    ))
    
    # Body text - override existing
    styles['BodyText'].fontSize = 10
    styles['BodyText'].textColor = colors.black
    styles['BodyText'].spaceAfter = 8
    styles['BodyText'].alignment = TA_JUSTIFY
    styles['BodyText'].leading = 14
    
    # Code style
    styles.add(ParagraphStyle(
        name='CodeBlock',
        parent=styles['Normal'],
        fontSize=9,
        fontName='Courier',
        textColor=colors.HexColor('#1F2937'),
        backColor=colors.HexColor('#F3F4F6'),
        spaceBefore=5,
        spaceAfter=5,
        leftIndent=10,
        rightIndent=10
    ))
    
    # Bullet point
    styles.add(ParagraphStyle(
        name='BulletItem',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.black,
        leftIndent=20,
        spaceAfter=4
    ))
    
    return styles

def build_document():
    """Build the complete documentation PDF"""
    doc = SimpleDocTemplate(
        "GW2_CounterPicker_Documentation.pdf",
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    styles = create_styles()
    story = []
    
    # ==================== TITLE PAGE ====================
    story.append(Spacer(1, 3*cm))
    story.append(Paragraph("🔮 GW2 CounterPicker", styles['DocTitle']))
    story.append(Paragraph("Documentation Technique Complète", styles['DocSubtitle']))
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph(f"Version 3.0 - {datetime.now().strftime('%d/%m/%Y')}", styles['DocSubtitle']))
    story.append(Spacer(1, 2*cm))
    story.append(Paragraph(
        "L'outil d'intelligence WvW le plus puissant jamais créé pour Guild Wars 2",
        styles['BodyText']
    ))
    story.append(PageBreak())
    
    # ==================== TABLE OF CONTENTS ====================
    story.append(Paragraph("📑 Table des Matières", styles['SectionHeader']))
    toc_items = [
        "1. Vue d'ensemble du projet",
        "2. Architecture technique",
        "3. Fonctionnalités principales",
        "4. Système de contexte de combat",
        "5. Analyse des performances",
        "6. Intégration API GW2",
        "7. Intelligence Artificielle",
        "8. Calculs et métriques",
        "9. Sécurité et stockage",
        "10. Déploiement"
    ]
    for item in toc_items:
        story.append(Paragraph(f"• {item}", styles['BulletItem']))
    story.append(PageBreak())
    
    # ==================== 1. VUE D'ENSEMBLE ====================
    story.append(Paragraph("1. Vue d'ensemble du projet", styles['SectionHeader']))
    story.append(Paragraph(
        "GW2 CounterPicker est une application web d'analyse de combats WvW (World vs World) "
        "pour Guild Wars 2. Elle permet aux joueurs et aux guildes d'analyser leurs performances, "
        "de comprendre les compositions ennemies et de recevoir des recommandations stratégiques "
        "personnalisées grâce à une intelligence artificielle.",
        styles['BodyText']
    ))
    
    story.append(Paragraph("Objectifs principaux", styles['SubsectionHeader']))
    objectives = [
        "Analyser les fichiers de combat EVTC générés par ArcDPS",
        "Fournir des statistiques détaillées par joueur et par escouade",
        "Détecter automatiquement les compositions ennemies",
        "Recommander des contre-compositions optimales via IA",
        "Suivre les performances individuelles et de guilde dans le temps",
        "Segmenter les données par contexte de combat (Zerg, Guild Raid, Roam)"
    ]
    for obj in objectives:
        story.append(Paragraph(f"• {obj}", styles['BulletItem']))
    
    story.append(Paragraph("Stack technique", styles['SubsectionHeader']))
    tech_data = [
        ["Composant", "Technologie"],
        ["Backend", "FastAPI 0.109+ (Python 3.11+)"],
        ["Frontend", "HTMX + Alpine.js + Tailwind CSS"],
        ["Templates", "Jinja2"],
        ["Base de données", "TinyDB (JSON)"],
        ["IA", "Ollama + Llama 3.2 8B"],
        ["PDF", "ReportLab"],
        ["API externe", "dps.report, API GW2 officielle"]
    ]
    tech_table = Table(tech_data, colWidths=[4*cm, 10*cm])
    tech_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PURPLE),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F9FAFB')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(tech_table)
    story.append(PageBreak())
    
    # ==================== 2. ARCHITECTURE ====================
    story.append(Paragraph("2. Architecture technique", styles['SectionHeader']))
    
    story.append(Paragraph("Structure des fichiers", styles['SubsectionHeader']))
    structure = """
gw2-counterpicker/
├── main.py                    # Application FastAPI principale
├── counter_ai.py              # IA de contre-attaque (Ollama)
├── counter_engine.py          # Moteur de contre-pick statique
├── parser.py                  # Parser EVTC natif
├── models.py                  # Modèles Pydantic
├── role_detector.py           # Détection automatique des rôles
├── translations.py            # Support multilingue FR/EN
│
├── services/
│   ├── gw2_api_service.py     # Intégration API GW2
│   ├── player_stats_service.py # Stats joueurs/guildes
│   ├── performance_stats_service.py # Comparaison gaussienne
│   ├── analysis_service.py    # Service d'analyse
│   └── file_validator.py      # Validation fichiers
│
├── routers/
│   ├── gw2_api.py             # Routes API GW2
│   ├── analysis.py            # Routes d'analyse
│   └── pages.py               # Routes de pages
│
├── templates/                 # Templates Jinja2
├── static/                    # Assets statiques
└── data/                      # Bases TinyDB (JSON)
"""
    for line in structure.strip().split('\n'):
        story.append(Paragraph(line, styles['CodeBlock']))
    
    story.append(Paragraph("Flux de données", styles['SubsectionHeader']))
    story.append(Paragraph(
        "1. L'utilisateur upload un fichier .evtc/.zevtc ou colle un lien dps.report",
        styles['BulletItem']
    ))
    story.append(Paragraph(
        "2. Le système vérifie que c'est un log WvW (filtre PvE/PvP)",
        styles['BulletItem']
    ))
    story.append(Paragraph(
        "3. Le fichier est parsé via dps.report (online) ou le parser local (offline)",
        styles['BulletItem']
    ))
    story.append(Paragraph(
        "4. Les données sont extraites : joueurs, stats, boons, composition",
        styles['BulletItem']
    ))
    story.append(Paragraph(
        "5. Le contexte de combat est détecté (Zerg/Guild/Roam)",
        styles['BulletItem']
    ))
    story.append(Paragraph(
        "6. Les stats sont enregistrées dans TinyDB pour l'historique",
        styles['BulletItem']
    ))
    story.append(Paragraph(
        "7. L'IA génère des recommandations de contre-composition",
        styles['BulletItem']
    ))
    story.append(PageBreak())
    
    # ==================== 3. FONCTIONNALITÉS ====================
    story.append(Paragraph("3. Fonctionnalités principales", styles['SectionHeader']))
    
    story.append(Paragraph("3.1 Analyse rapide (Single File)", styles['SubsectionHeader']))
    story.append(Paragraph(
        "Permet d'analyser un seul fichier de combat. L'utilisateur peut soit uploader "
        "un fichier .evtc/.zevtc directement, soit coller un lien dps.report existant.",
        styles['BodyText']
    ))
    single_features = [
        "Extraction des stats de tous les joueurs alliés",
        "Détection de la composition ennemie",
        "Calcul des DPS, soins, barrière, strips, cleanses, CC",
        "Génération de boons par joueur (Quickness, Stability, etc.)",
        "Détection automatique des rôles (DPS, Healer, Stab, Boon, Strip)",
        "Recommandation de contre-composition via IA"
    ]
    for f in single_features:
        story.append(Paragraph(f"• {f}", styles['BulletItem']))
    
    story.append(Paragraph("3.2 Analyse soirée (Multiple Files)", styles['SubsectionHeader']))
    story.append(Paragraph(
        "Permet d'analyser jusqu'à 100 fichiers simultanément pour obtenir une vue "
        "agrégée d'une session de jeu complète.",
        styles['BodyText']
    ))
    multi_features = [
        "Agrégation des statistiques sur tous les combats",
        "Comptage des victoires, défaites et nuls",
        "Déduplication des joueurs par nom de compte (account name)",
        "Calcul du nombre de joueurs uniques",
        "Composition moyenne de l'escouade",
        "Top 10 joueurs par dégâts",
        "Builds les plus joués par classe"
    ]
    for f in multi_features:
        story.append(Paragraph(f"• {f}", styles['BulletItem']))
    
    story.append(Paragraph("3.3 Dashboard personnel", styles['SubsectionHeader']))
    story.append(Paragraph(
        "Accessible après connexion avec une clé API GW2. Affiche les statistiques "
        "personnelles du joueur et ses guildes.",
        styles['BodyText']
    ))
    dashboard_features = [
        "Informations du compte GW2 (nom, monde, rang WvW)",
        "Liste de toutes les guildes du joueur",
        "Statistiques de carrière (combats, victoires, temps de jeu)",
        "Import des combats depuis la base de données IA"
    ]
    for f in dashboard_features:
        story.append(Paragraph(f"• {f}", styles['BulletItem']))
    
    story.append(Paragraph("3.4 Historique des combats", styles['SubsectionHeader']))
    story.append(Paragraph(
        "Affiche l'historique des combats du joueur avec des statistiques détaillées "
        "par spécialisation et une comparaison de performance.",
        styles['BodyText']
    ))
    
    story.append(Paragraph("3.5 Analytics de guilde", styles['SubsectionHeader']))
    story.append(Paragraph(
        "Vue dédiée aux statistiques d'une guilde spécifique, incluant les membres "
        "actifs, la répartition des rôles et les meilleures compositions de groupe.",
        styles['BodyText']
    ))
    story.append(PageBreak())
    
    # ==================== 4. CONTEXTE DE COMBAT ====================
    story.append(Paragraph("4. Système de contexte de combat", styles['SectionHeader']))
    story.append(Paragraph(
        "Le système de contexte permet de segmenter les données WvW en 3 catégories "
        "distinctes, car les métas et stratégies diffèrent selon le type de combat.",
        styles['BodyText']
    ))
    
    story.append(Paragraph("4.1 Types de contexte", styles['SubsectionHeader']))
    context_data = [
        ["Contexte", "Description", "Critères"],
        ["Zerg", "Combats de masse blob vs blob", "≥25 alliés OU ≥30 ennemis"],
        ["Guild Raid", "Combats de guilde structurés", "10-25 alliés + cohésion guilde ≥50%"],
        ["Roam", "Petit comité / roaming", "≤10 alliés ET ≤12 ennemis"],
        ["Unknown", "Cas ambigus", "Zone grise entre les catégories"]
    ]
    context_table = Table(context_data, colWidths=[2.5*cm, 5*cm, 6.5*cm])
    context_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PURPLE),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F9FAFB')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(context_table)
    
    story.append(Paragraph("4.2 Algorithme de détection", styles['SubsectionHeader']))
    story.append(Paragraph(
        "La fonction guess_fight_context() utilise plusieurs paramètres pour déterminer "
        "automatiquement le contexte d'un combat :",
        styles['BodyText']
    ))
    algo_params = [
        "ally_count : Nombre de joueurs alliés dans le combat",
        "enemy_count : Estimation du nombre d'ennemis",
        "duration_sec : Durée du combat en secondes",
        "subgroup_count : Nombre de sous-groupes distincts",
        "main_guild_ratio : Ratio de joueurs de la guilde dominante (0.0-1.0)"
    ]
    for p in algo_params:
        story.append(Paragraph(f"• {p}", styles['BulletItem']))
    
    story.append(Paragraph("4.3 Sélection manuelle", styles['SubsectionHeader']))
    story.append(Paragraph(
        "L'utilisateur peut également sélectionner manuellement le contexte via un "
        "sélecteur visuel sur la page d'analyse. Le contexte confirmé par l'utilisateur "
        "(context_confirmed) prend priorité sur le contexte détecté (context_detected).",
        styles['BodyText']
    ))
    
    story.append(Paragraph("4.4 Pages META par contexte", styles['SubsectionHeader']))
    story.append(Paragraph(
        "La page META est disponible en 4 versions filtrées :",
        styles['BodyText']
    ))
    meta_routes = [
        "/meta - Tous les contextes combinés",
        "/meta/zerg - Statistiques Zerg uniquement",
        "/meta/guild_raid - Statistiques Guild Raid uniquement",
        "/meta/roam - Statistiques Roam uniquement"
    ]
    for r in meta_routes:
        story.append(Paragraph(f"• {r}", styles['BulletItem']))
    story.append(PageBreak())
    
    # ==================== 5. ANALYSE DES PERFORMANCES ====================
    story.append(Paragraph("5. Analyse des performances", styles['SectionHeader']))
    
    story.append(Paragraph("5.1 Comparaison gaussienne", styles['SubsectionHeader']))
    story.append(Paragraph(
        "Le système calcule et stocke des statistiques globales pour permettre aux "
        "joueurs de comparer leurs performances à l'ensemble de la communauté. "
        "Les métriques suivent une distribution gaussienne (normale).",
        styles['BodyText']
    ))
    
    story.append(Paragraph("5.2 Catégories de métriques", styles['SubsectionHeader']))
    metrics_data = [
        ["Catégorie", "Indicateurs utilisés"],
        ["DPS", "Damage per second, Down contribution per second"],
        ["Strip", "Strips per second, CC per second"],
        ["Boon", "Quickness, Resistance, Aegis, Superspeed, Stability, Protection, Vigor, Might, Fury, Regeneration, Resolution, Swiftness, Alacrity (par seconde)"],
        ["Stab", "Aegis per second, Stability per second"],
        ["Heal", "Regeneration, Outgoing healing, Barrier, Cleanses, Resurrects (par seconde)"]
    ]
    metrics_table = Table(metrics_data, colWidths=[2*cm, 12*cm])
    metrics_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PURPLE),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F9FAFB')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(metrics_table)
    
    story.append(Paragraph("5.3 Algorithme de Welford", styles['SubsectionHeader']))
    story.append(Paragraph(
        "Pour calculer la moyenne et l'écart-type de manière incrémentale (sans stocker "
        "toutes les valeurs), le système utilise l'algorithme de Welford :",
        styles['BodyText']
    ))
    story.append(Paragraph(
        "Pour chaque nouvelle valeur x :",
        styles['BodyText']
    ))
    welford_steps = [
        "n = n + 1",
        "delta = x - mean",
        "mean = mean + delta / n",
        "M2 = M2 + delta * (x - mean)",
        "variance = M2 / n (si n > 1)"
    ]
    for s in welford_steps:
        story.append(Paragraph(f"• {s}", styles['BulletItem']))
    
    story.append(Paragraph("5.4 Calcul du percentile", styles['SubsectionHeader']))
    story.append(Paragraph(
        "Le percentile d'un joueur est calculé via la fonction de répartition cumulative "
        "(CDF) de la distribution normale :",
        styles['BodyText']
    ))
    story.append(Paragraph("z_score = (valeur - moyenne) / écart_type", styles['CodeBlock']))
    story.append(Paragraph("percentile = Φ(z_score) × 100", styles['CodeBlock']))
    
    story.append(Paragraph("5.5 Ratings", styles['SubsectionHeader']))
    rating_data = [
        ["Percentile", "Rating", "Description"],
        ["≥95%", "Exceptionnel", "Top 5% des joueurs"],
        ["≥75%", "Au-dessus", "Meilleur que 75% des joueurs"],
        ["≥25%", "Moyenne", "Dans la norme"],
        ["<25%", "En dessous", "Marge de progression"]
    ]
    rating_table = Table(rating_data, colWidths=[3*cm, 3*cm, 8*cm])
    rating_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PURPLE),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F9FAFB')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
    ]))
    story.append(rating_table)
    story.append(PageBreak())
    
    # ==================== 6. API GW2 ====================
    story.append(Paragraph("6. Intégration API GW2", styles['SectionHeader']))
    
    story.append(Paragraph("6.1 Connexion", styles['SubsectionHeader']))
    story.append(Paragraph(
        "L'utilisateur peut connecter son compte GW2 en fournissant une clé API "
        "générée sur le site officiel d'ArenaNet. La clé est stockée de manière "
        "sécurisée avec chiffrement Fernet.",
        styles['BodyText']
    ))
    
    story.append(Paragraph("6.2 Données récupérées", styles['SubsectionHeader']))
    api_data = [
        "Informations du compte (nom, monde, rang WvW)",
        "Liste des guildes du joueur",
        "Membres d'une guilde (si l'utilisateur a les permissions)",
        "Personnages du compte"
    ]
    for d in api_data:
        story.append(Paragraph(f"• {d}", styles['BulletItem']))
    
    story.append(Paragraph("6.3 Endpoints utilisés", styles['SubsectionHeader']))
    endpoints = [
        "GET /v2/account - Informations du compte",
        "GET /v2/account/guilds - Liste des guildes",
        "GET /v2/guild/{id} - Détails d'une guilde",
        "GET /v2/guild/{id}/members - Membres d'une guilde",
        "GET /v2/characters - Liste des personnages"
    ]
    for e in endpoints:
        story.append(Paragraph(f"• {e}", styles['BulletItem']))
    story.append(PageBreak())
    
    # ==================== 7. INTELLIGENCE ARTIFICIELLE ====================
    story.append(Paragraph("7. Intelligence Artificielle", styles['SectionHeader']))
    
    story.append(Paragraph("7.1 Architecture", styles['SubsectionHeader']))
    story.append(Paragraph(
        "L'IA utilise Ollama avec le modèle Llama 3.2 8B pour générer des recommandations "
        "de contre-composition personnalisées. Elle apprend de chaque combat uploadé.",
        styles['BodyText']
    ))
    
    story.append(Paragraph("7.2 Base de connaissances", styles['SubsectionHeader']))
    story.append(Paragraph(
        "Chaque combat analysé est enregistré dans une base TinyDB avec :",
        styles['BodyText']
    ))
    ai_data = [
        "Composition ennemie détaillée",
        "Composition alliée avec builds détaillés",
        "Résultat (victoire/défaite/nul)",
        "Durée et statistiques de combat",
        "Contexte de combat (Zerg/Guild/Roam)"
    ]
    for d in ai_data:
        story.append(Paragraph(f"• {d}", styles['BulletItem']))
    
    story.append(Paragraph("7.3 Prompts contextualisés", styles['SubsectionHeader']))
    story.append(Paragraph(
        "L'IA utilise des prompts système différents selon le contexte de combat :",
        styles['BodyText']
    ))
    prompts = [
        "Zerg : Focus sur les AOE, le timing, la survie dans le blob, les skills de masse",
        "Guild Raid : Focus sur les synergies de composition, les rôles précis, la discipline",
        "Roam : Focus sur le 1v1, le burst, la mobilité, le disengage"
    ]
    for p in prompts:
        story.append(Paragraph(f"• {p}", styles['BulletItem']))
    
    story.append(Paragraph("7.4 Recherche de combats similaires", styles['SubsectionHeader']))
    story.append(Paragraph(
        "Avant de générer une recommandation, l'IA recherche des combats similaires "
        "dans la base de données en filtrant par :",
        styles['BodyText']
    ))
    similar_criteria = [
        "Contexte de combat identique",
        "Composition ennemie proche (specs similaires)",
        "Résultat (priorité aux victoires pour apprendre ce qui fonctionne)"
    ]
    for c in similar_criteria:
        story.append(Paragraph(f"• {c}", styles['BulletItem']))
    story.append(PageBreak())
    
    # ==================== 8. CALCULS ET MÉTRIQUES ====================
    story.append(Paragraph("8. Calculs et métriques", styles['SectionHeader']))
    
    story.append(Paragraph("8.1 Détection des rôles", styles['SubsectionHeader']))
    story.append(Paragraph(
        "Le système détecte automatiquement le rôle de chaque joueur basé sur sa "
        "spécialisation élite et ses statistiques :",
        styles['BodyText']
    ))
    roles_data = [
        ["Rôle", "Critères"],
        ["DPS", "Spécialisations offensives (Berserker, Reaper, Weaver...)"],
        ["Healer", "Spécialisations de soin (Druid, Tempest, Firebrand...)"],
        ["Stab", "Génération de Stability élevée"],
        ["Boon", "Génération de boons élevée (Quickness, Alacrity...)"],
        ["Strip", "Strips et CC élevés (Spellbreaker, Scourge...)"]
    ]
    roles_table = Table(roles_data, colWidths=[2.5*cm, 11.5*cm])
    roles_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PURPLE),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F9FAFB')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
    ]))
    story.append(roles_table)
    
    story.append(Paragraph("8.2 Calcul du résultat", styles['SubsectionHeader']))
    story.append(Paragraph(
        "Le résultat d'un combat est déterminé par le ratio de morts :",
        styles['BodyText']
    ))
    story.append(Paragraph("ratio = enemy_deaths / max(ally_deaths, 1)", styles['CodeBlock']))
    outcome_rules = [
        "Victoire : ratio ≥ 1.5 (50% plus de morts ennemis)",
        "Défaite : ratio ≤ 0.67 (50% plus de morts alliés)",
        "Nul : entre 0.67 et 1.5"
    ]
    for r in outcome_rules:
        story.append(Paragraph(f"• {r}", styles['BulletItem']))
    
    story.append(Paragraph("8.3 Filtre WvW", styles['SubsectionHeader']))
    story.append(Paragraph(
        "Le système filtre automatiquement les logs PvE et PvP pour n'accepter que "
        "les combats WvW. Les critères de détection sont :",
        styles['BodyText']
    ))
    wvw_criteria = [
        "Présence de cibles avec enemyPlayer: true",
        "Absence de triggerID correspondant à des boss PvE connus",
        "fightName ne contenant pas de noms de boss (Vale Guardian, Dhuum...)",
        "isCM = false (pas de Challenge Mode)",
        "isTrainingGolem = false"
    ]
    for c in wvw_criteria:
        story.append(Paragraph(f"• {c}", styles['BulletItem']))
    
    story.append(Paragraph("8.4 Boon Generation", styles['SubsectionHeader']))
    story.append(Paragraph(
        "La génération de boons est calculée en pourcentage d'uptime sur la durée "
        "du combat. Le système supporte deux modes d'affichage :",
        styles['BodyText']
    ))
    boon_modes = [
        "Group : Génération sur le groupe du joueur (5 joueurs)",
        "Squad : Génération sur l'escouade entière (jusqu'à 50 joueurs)"
    ]
    for m in boon_modes:
        story.append(Paragraph(f"• {m}", styles['BulletItem']))
    story.append(PageBreak())
    
    # ==================== 9. SÉCURITÉ ====================
    story.append(Paragraph("9. Sécurité et stockage", styles['SectionHeader']))
    
    story.append(Paragraph("9.1 Rate limiting", styles['SubsectionHeader']))
    story.append(Paragraph(
        "Le système limite le nombre de requêtes par IP pour éviter les abus :",
        styles['BodyText']
    ))
    story.append(Paragraph("• 10 uploads par minute par IP", styles['BulletItem']))
    
    story.append(Paragraph("9.2 Validation des fichiers", styles['SubsectionHeader']))
    story.append(Paragraph(
        "Tous les fichiers uploadés sont validés :",
        styles['BodyText']
    ))
    validation_rules = [
        "Taille maximale : 50 MB",
        "Extensions autorisées : .evtc, .zevtc, .zip",
        "Vérification du contenu (signature de fichier)"
    ]
    for r in validation_rules:
        story.append(Paragraph(f"• {r}", styles['BulletItem']))
    
    story.append(Paragraph("9.3 Chiffrement des clés API", styles['SubsectionHeader']))
    story.append(Paragraph(
        "Les clés API GW2 sont chiffrées avec Fernet (AES-128-CBC) avant stockage. "
        "La clé de chiffrement est générée au premier démarrage et stockée dans "
        "les variables d'environnement.",
        styles['BodyText']
    ))
    
    story.append(Paragraph("9.4 Bases de données TinyDB", styles['SubsectionHeader']))
    db_files = [
        "data/ai_fights.json - Combats pour apprentissage IA",
        "data/sessions.json - Sessions utilisateurs",
        "data/player_stats.json - Statistiques individuelles",
        "data/guild_stats.json - Statistiques de guilde",
        "data/performance_stats.json - Métriques globales de performance",
        "data/api_keys.json - Clés API chiffrées"
    ]
    for f in db_files:
        story.append(Paragraph(f"• {f}", styles['BulletItem']))
    story.append(PageBreak())
    
    # ==================== 10. DÉPLOIEMENT ====================
    story.append(Paragraph("10. Déploiement", styles['SectionHeader']))
    
    story.append(Paragraph("10.1 Prérequis", styles['SubsectionHeader']))
    prereqs = [
        "Python 3.11+",
        "pip (gestionnaire de paquets Python)",
        "Ollama (optionnel, pour l'IA)"
    ]
    for p in prereqs:
        story.append(Paragraph(f"• {p}", styles['BulletItem']))
    
    story.append(Paragraph("10.2 Installation locale", styles['SubsectionHeader']))
    install_steps = [
        "git clone https://github.com/Roddygithub/gw2-counterpicker.git",
        "cd gw2-counterpicker",
        "python -m venv venv",
        "source venv/bin/activate",
        "pip install -r requirements.txt",
        "python main.py"
    ]
    for s in install_steps:
        story.append(Paragraph(s, styles['CodeBlock']))
    
    story.append(Paragraph("10.3 Variables d'environnement", styles['SubsectionHeader']))
    env_vars = [
        "FERNET_KEY - Clé de chiffrement pour les API keys",
        "OLLAMA_URL - URL du serveur Ollama (défaut: http://localhost:11434)"
    ]
    for v in env_vars:
        story.append(Paragraph(f"• {v}", styles['BulletItem']))
    
    story.append(Paragraph("10.4 Docker", styles['SubsectionHeader']))
    story.append(Paragraph(
        "L'image Docker embarque uvicorn pour la production.",
        styles['BodyText']
    ))
    docker_cmds = [
        "docker build -t gw2-counterpicker .",
        "docker run -p 8000:8000 gw2-counterpicker"
    ]
    for c in docker_cmds:
        story.append(Paragraph(c, styles['CodeBlock']))
    
    # ==================== 11. GUIDE DE CONTRIBUTION ====================
    story.append(PageBreak())
    story.append(Paragraph("11. Guide de contribution", styles['SectionHeader']))
    
    story.append(Paragraph("11.1 Lancement des tests", styles['SubsectionHeader']))
    test_steps = [
        "pip install -r requirements-dev.txt",
        "pytest"
    ]
    for s in test_steps:
        story.append(Paragraph(s, styles['CodeBlock']))
    
    story.append(Paragraph("11.2 Organisation du code", styles['SubsectionHeader']))
    story.append(Paragraph(
        "Le projet suit une architecture claire pour faciliter les contributions :",
        styles['BodyText']
    ))
    org_data = [
        ["Dossier/Fichier", "Role"],
        ["routers/", "Endpoints HTTP (routes publiques et API)"],
        ["services/", "Logique metier (calculs, traitements)"],
        ["counter_ai.py", "IA et apprentissage (Ollama)"],
        ["parser.py", "Parsing natif des fichiers EVTC"],
        ["models.py", "Modeles Pydantic pour la validation"],
        ["templates/", "Templates Jinja2 pour le frontend"]
    ]
    org_table = Table(org_data, colWidths=[3*cm, 11*cm])
    org_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PURPLE),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F9FAFB')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
    ]))
    story.append(org_table)
    
    story.append(Paragraph("11.3 Conventions", styles['SubsectionHeader']))
    conventions = [
        "Ajouter une nouvelle route : Creer un endpoint dans routers/ correspondant",
        "Ajouter un nouveau service : Creer un fichier dans services/ avec la logique",
        "Logging : Utiliser logger.getLogger(__name__) dans chaque module",
        "Variables : snake_case pour Python, camelCase pour JavaScript",
        "Commits : Utiliser des messages clairs et descriptifs"
    ]
    for c in conventions:
        story.append(Paragraph(f"- {c}", styles['BulletItem']))
    
    # ==================== 12. EXEMPLE DE FLOW ====================
    story.append(PageBreak())
    story.append(Paragraph("12. Exemple de flow end-to-end", styles['SectionHeader']))
    story.append(Paragraph(
        "Scenario complet : Un joueur upload un fichier de combat",
        styles['BodyText']
    ))
    flow_steps = [
        "1. Le joueur upload 20251205-233553.zevtc sur /analyze",
        "2. file_validator verifie la taille, l'extension et le contenu ZIP",
        "3. analysis_service essaye d'abord d'appeler dps.report (online)",
        "4. Si echec, fallback sur le parser local (offline)",
        "5. Les stats sont envoyees a role_detector pour identifier les roles",
        "6. performance_stats_service.record_player_performance enregistre les metriques",
        "7. Si une cle API GW2 est liee, player_stats_service enregistre dans l'historique",
        "8. counter_ai enregistre le combat dans ai_fights.json pour l'apprentissage",
        "9. FastAPI rend dps_report_result.html avec l'IA et les onglets de stats"
    ]
    for f in flow_steps:
        story.append(Paragraph(f"- {f}", styles['BulletItem']))
    
    # ==================== 13. ENDPOINTS ====================
    story.append(PageBreak())
    story.append(Paragraph("13. Recapitulatif des endpoints", styles['SectionHeader']))
    
    story.append(Paragraph("13.1 Endpoints publics (HTML)", styles['SubsectionHeader']))
    html_endpoints = [
        ["Methode", "Route", "Description"],
        ["GET", "/", "Page d'accueil"],
        ["GET", "/analyze", "Formulaire d'analyse"],
        ["POST", "/analyze", "Upload de logs + analyse"],
        ["GET", "/meta", "Meta globale"],
        ["GET", "/meta/zerg", "Meta context Zerg"],
        ["GET", "/meta/guild_raid", "Meta context Guild Raid"],
        ["GET", "/meta/roam", "Meta context Roam"],
        ["GET", "/dashboard", "Dashboard perso (cle API requise)"],
        ["GET", "/history", "Historique perso"],
        ["GET", "/guild/{id}", "Analytics guilde"]
    ]
    html_table = Table(html_endpoints, colWidths=[2*cm, 4*cm, 8*cm])
    html_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PURPLE),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F9FAFB')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
    ]))
    story.append(html_table)
    
    story.append(Paragraph("13.2 Endpoints API (JSON)", styles['SubsectionHeader']))
    api_endpoints = [
        ["Methode", "Route", "Description", "Auth"],
        ["GET", "/api/gw2/stats", "Stats carriere du compte", "Session"],
        ["GET", "/api/gw2/stats/specs", "Stats par specialisation", "Session"],
        ["GET", "/api/gw2/fights", "Historique des combats", "Session"],
        ["GET", "/api/gw2/guilds", "Liste des guildes", "Session"],
        ["GET", "/api/gw2/guild/{id}", "Stats detaillees guilde", "Session"],
        ["GET", "/api/gw2/recommendations", "Recommandations IA perso", "Session"]
    ]
    api_table = Table(api_endpoints, colWidths=[2*cm, 4*cm, 5*cm, 2*cm])
    api_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PURPLE),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F9FAFB')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
    ]))
    story.append(api_table)
    
    # ==================== 14. LIMITATIONS ====================
    story.append(PageBreak())
    story.append(Paragraph("14. Limitations connues", styles['SectionHeader']))
    limitations = [
        "La detection de contexte (Zerg/Guild/Roam) repose sur des heuristiques + corrections utilisateurs",
        "Les stats meta peuvent etre biaisees vers les guildes/joueurs qui utilisent l'outil",
        "Les recommandations IA ne connaissent pas les builds/traits/equipements exacts des ennemis",
        "Seules les specialisations sont detectees, pas les traits ou runes specifiques",
        "L'IA depend de la disponibilite d'Ollama et du modele Llama 3.2"
    ]
    for l in limitations:
        story.append(Paragraph(f"- {l}", styles['BulletItem']))
    
    story.append(Paragraph("14.1 Avertissement IA", styles['SubsectionHeader']))
    story.append(Paragraph(
        "Les recommandations IA sont basees sur les combats enregistres via GW2 CounterPicker "
        "et sur un modele de langage generaliste. Elles ne sont pas garanties optimales et "
        "doivent etre utilisees comme aide a la decision, pas comme verite absolue.",
        styles['BodyText']
    ))
    
    # ==================== 15. SECURITE & RGPD ====================
    story.append(PageBreak())
    story.append(Paragraph("15. Securite et RGPD", styles['SectionHeader']))
    
    story.append(Paragraph("15.1 Donnees collectees", styles['SubsectionHeader']))
    data_collected = [
        "Cles API GW2 (chiffrees avec Fernet)",
        "Nom de compte et personnages GW2",
        "Historique des combats analyses",
        "Statistiques de performance agregees",
        "Adresse IP (logs temporaires)"
    ]
    for d in data_collected:
        story.append(Paragraph(f"- {d}", styles['BulletItem']))
    
    story.append(Paragraph("15.2 Retention des donnees", styles['SubsectionHeader']))
    story.append(Paragraph(
        "Les stats de combats sont conservees 6 mois. Les cles API sont stockees "
        "jusqu'a suppression par l'utilisateur. Les logs serveur sont conserves 30 jours.",
        styles['BodyText']
    ))
    
    story.append(Paragraph("15.3 Suppression des donnees", styles['SubsectionHeader']))
    story.append(Paragraph(
        "Pour demander la suppression de vos donnees, contactez l'administrateur "
        "via l'adresse email du projet. Un bouton de suppression automatique "
        "sera ajoute dans une future version du dashboard.",
        styles['BodyText']
    ))
    
    story.append(Spacer(1, 2*cm))
    story.append(Paragraph(
        f"Documentation generee le {datetime.now().strftime('%d/%m/%Y a %H:%M')}",
        styles['DocSubtitle']
    ))
    story.append(Paragraph(
        "GW2 CounterPicker - Made with rage, love and 15 years of WvW pain.",
        styles['DocSubtitle']
    ))
    
    # Build PDF
    doc.build(story)
    print("✅ Documentation générée : GW2_CounterPicker_Documentation.pdf")

if __name__ == "__main__":
    build_document()
