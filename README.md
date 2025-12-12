# 🔮 GW2 CounterPicker

<div align="center">

![GW2 CounterPicker Banner](https://via.placeholder.com/1200x400/0F0A1F/8B5CF6?text=GW2+CounterPicker)

### **Le seul outil capable de lire dans l'âme de ton adversaire.**
### **Et dans celle de tout son serveur.**

[![Live Demo](https://img.shields.io/badge/🚀_Live_Demo-Render-8B5CF6?style=for-the-badge)](https://gw2-counterpicker.onrender.com)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

---

**L'outil d'intelligence WvW le plus puissant jamais créé pour Guild Wars 2.**

*Made with rage, love and 15 years of WvW pain.* 💜

[🚀 Demo Live](#demo) • [⚡ Quick Start](#quick-start) • [📖 Documentation](#features) • [🤝 Contribuer](#contributing)

</div>

---

## 🎬 Demo

![Demo GIF](https://via.placeholder.com/800x450/0F0A1F/EC4899?text=Demo+Video+Coming+Soon)

> *Capture d'écran de l'interface en action - Coming soon*

---

## ⚡ Features

### 🎯 Mode 1: Quick Analysis
- **Colle un lien dps.report** → Analyse complète en **3 secondes**
- Détection automatique de la composition ennemie
- Counter parfait recommandé avec stratégie détaillée
- Identification des specs dominantes et du type de squad

### 📊 Mode 2: Soirée Complète
- **Drag & drop jusqu'à 100 fichiers .evtc/.zip**
- Analyse exhaustive de 4+ heures de WvW
- **Composition moyenne** du serveur adverse
- **Évolution horaire** des builds (ex: "À 21h30 → 8 FB, à 23h15 → 14 FB")
- **Heatmap** des zones les plus contestées
- **Top 10** joueurs les plus vus + leurs builds exacts
- Build le plus joué par classe
- **Counter parfait** pour le prochain soir
- 📄 **Export PDF** "Night Intelligence Report"

### 📈 Meta 2025
- Tier list actualisée des builds WvW EU
- Specs en hausse et en baisse
- Analyse des tendances meta

### 🎨 Design Cyberpunk
- UI moderne avec thème nebula violet-bleu
- Animations fluides HTMX + Alpine.js
- 100% responsive (mobile, tablette, desktop)
- Mode sombre élégant

---

## 🚀 Quick Start

### Prérequis
- Python 3.11+
- pip

### Installation locale

```bash
# Clone le repo
git clone https://github.com/YOUR_USERNAME/gw2-counterpicker.git
cd gw2-counterpicker

# Crée un environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou: venv\Scripts\activate  # Windows

# Installe les dépendances
pip install -r requirements.txt

# Lance le serveur
python main.py
```

Ouvre http://localhost:8000 dans ton navigateur 🎉

### Docker

```bash
docker build -t gw2-counterpicker .
docker run -p 8000:8000 gw2-counterpicker
```

---

## 🌐 Déploiement

### Render (Recommandé)

1. Fork ce repo
2. Connecte-toi sur [render.com](https://render.com)
3. Crée un nouveau "Web Service"
4. Connecte ton repo GitHub
5. Configure:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Deploy! 🚀

### Railway

```bash
railway login
railway init
railway up
```

### Fly.io

```bash
fly launch
fly deploy
```

---

## 🛠️ Stack Technique

| Composant | Technologie |
|-----------|-------------|
| Backend | **FastAPI** 0.109 |
| Frontend | **HTMX** + **Alpine.js** |
| Styling | **Tailwind CSS** (CDN) |
| Templating | **Jinja2** |
| PDF Generation | **ReportLab** |
| Fonts | **Orbitron** + **Inter** |

---

## 📁 Structure du Projet

```
gw2-counterpicker/
├── main.py              # FastAPI application
├── models.py            # Pydantic data models
├── mock_parser.py       # EVTC parser (mock for now)
├── counter_engine.py    # Counter-pick intelligence
├── pdf_generator.py     # PDF report generation
├── requirements.txt     # Python dependencies
├── Dockerfile           # Docker configuration
├── render.yaml          # Render deployment config
├── templates/           # Jinja2 templates
│   ├── base.html
│   ├── index.html
│   ├── analyze.html
│   ├── evening.html
│   ├── meta.html
│   └── partials/
│       ├── analysis_result.html
│       └── evening_result.html
└── static/
    ├── css/
    └── js/
```

---

## 🔮 Roadmap

- [x] Mode Quick Analysis (dps.report)
- [x] Mode Soirée Complète (multi-fichiers)
- [x] Counter-pick engine intelligent
- [x] Export PDF Night Intelligence Report
- [x] Meta 2025 tier list
- [ ] **Vrai parsing .evtc** avec python-evtc
- [ ] Login GitHub OAuth
- [ ] Sauvegarde des analyses
- [ ] Partage public de rapports
- [ ] API publique
- [ ] Intégration Discord bot
- [ ] Historique des matchups

---

## 🤝 Contributing

Les PRs sont les bienvenues! Pour les changements majeurs, ouvre d'abord une issue.

```bash
# Fork le projet
# Crée ta branche
git checkout -b feature/amazing-feature

# Commit
git commit -m 'Add amazing feature'

# Push
git push origin feature/amazing-feature

# Ouvre une Pull Request
```

---

## 📜 License

MIT License - voir [LICENSE](LICENSE) pour les détails.

---

## 💜 Credits

- **Guild Wars 2** est une marque déposée d'ArenaNet, LLC.
- Ce projet n'est pas affilié à ArenaNet ou NCSOFT.
- Icônes par [Lucide](https://lucide.dev)
- Inspiré par 15 ans de souffrance en WvW

---

<div align="center">

### 🔮 *"Demain matin, quand les commandants EU se lèvent, ils découvriront que la guerre vient de changer pour toujours."*

**Made with rage, love and 15 years of WvW pain.** 💜

---

⭐ **Star ce repo si tu veux dominer le WvW!** ⭐

</div>
