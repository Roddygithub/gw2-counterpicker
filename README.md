# 🔮 GW2 CounterPicker v4.0

<div align="center">

![GW2 CounterPicker Banner](https://via.placeholder.com/1200x400/0F0A1F/8B5CF6?text=GW2+CounterPicker+v4.0)

### **Stats-Based WvW Intelligence Engine**
### **Analyse. Apprends. Domine.**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Tests](https://img.shields.io/badge/Tests-Passing-success?style=for-the-badge)](https://github.com/Roddygithub/gw2-counterpicker/actions)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

---

**L'outil d'intelligence WvW basé sur les données réelles de combat.**

*Propulsé par l'analyse statistique de milliers de fights WvW.* 💜

[⚡ Quick Start](#quick-start) • [📖 Features](#features) • [🚀 Déploiement](#déploiement) • [🤝 Contribuer](#contributing)

</div>

---

## 🎯 Version 4.0 - Core Engine

**Changements majeurs :**
- ✅ **Moteur stats-based** : Recommandations basées sur l'historique réel de combats
- ✅ **Zero dépendances LLM** : Plus rapide, plus léger, plus fiable
- ✅ **Tests automatisés** : 20+ tests avec CI/CD
- ✅ **Déploiement automatique** : GitHub Actions → Production
- ✅ **Architecture propre** : Services séparés, code maintenable

---

## ⚡ Features

### 🎯 Analyse de Combats
- **Upload dps.report ou fichiers .evtc/.zevtc**
- Détection automatique du contexte (Zerg/Guild Raid/Roam)
- Analyse détaillée de la composition ennemie
- Statistiques par joueur et par squad
- Déduplication intelligente des combats

### 🧠 Recommandations Stats-Based
- **Counters basés sur l'historique réel** de tes combats
- Analyse des builds qui ont gagné contre des compos similaires
- Taux de victoire par build et par contexte
- Stratégies adaptées au type de combat
- Système de feedback pour améliorer les recommandations

### 📊 Analyse Multi-Fichiers
- **Upload jusqu'à 100 fichiers** en une fois
- Analyse agrégée d'une soirée complète
- **Top 10 joueurs** les plus rencontrés
- Composition moyenne de l'adversaire
- Statistiques de victoires/défaites
- Export PDF des résultats

### 📈 Meta WvW
- Pages meta par contexte (Zerg/Guild Raid/Roam/Unknown)
- Builds les plus joués basés sur les données réelles
- Tier list actualisée automatiquement
- Tendances et évolution du meta

### 🎨 Interface Moderne
- UI cyberpunk avec thème violet-bleu
- Animations fluides (HTMX + Alpine.js)
- 100% responsive
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

### Production (SSH + systemd)

Voir [DEPLOYMENT.md](DEPLOYMENT.md) pour le guide complet.

```bash
# Sur le serveur
sudo systemctl start gw2-counterpicker
sudo systemctl enable gw2-counterpicker
```

---

## 🛠️ Stack Technique

| Composant | Technologie |
|-----------|-------------|
| Backend | **FastAPI** 0.109 |
| Database | **TinyDB** (JSON) |
| Parser | **python-evtc** (EVTC parsing) |
| Frontend | **HTMX** + **Alpine.js** |
| Styling | **Tailwind CSS** (CDN) |
| Templating | **Jinja2** |
| PDF Generation | **ReportLab** |
| Testing | **pytest** + **pytest-asyncio** |
| CI/CD | **GitHub Actions** |
| Deployment | **SSH** (systemd + nginx) |

---

## 📁 Structure du Projet

```
gw2-counterpicker/
├── main.py                      # FastAPI application
├── models.py                    # Pydantic models
├── parser.py                    # EVTC parser
├── counter_engine.py            # Rules-based counter logic
├── role_detector.py             # Role detection
├── pdf_generator.py             # PDF generation
├── services/
│   ├── counter_service.py       # Stats-based counter engine
│   ├── analysis_service.py      # Fight analysis
│   ├── player_stats_service.py  # Player statistics
│   ├── performance_stats_service.py
│   ├── gw2_api_service.py       # GW2 API integration
│   └── file_validator.py        # Security validation
├── routers/
│   ├── analysis.py              # Analysis endpoints
│   ├── pages.py                 # Web pages
│   ├── admin.py                 # Admin endpoints
│   └── gw2_api.py               # GW2 API endpoints
├── tests/
│   ├── test_counter_service.py  # Counter service tests
│   ├── test_analysis_service.py
│   └── test_role_detector.py
├── templates/                   # Jinja2 templates
├── static/                      # CSS, JS, images
├── data/                        # TinyDB databases
└── .github/workflows/           # CI/CD
    └── test-and-deploy.yml
```

---

## 🔮 Roadmap

### v4.0 - Core Engine ✅
- [x] Moteur stats-based sans LLM
- [x] Tests automatisés (pytest)
- [x] CI/CD avec GitHub Actions
- [x] Déploiement automatique
- [x] Architecture propre (services/routers)
- [x] Parsing EVTC complet
- [x] Analyse multi-fichiers
- [x] Export PDF
- [x] Meta pages par contexte
- [x] GW2 API integration

### v4.1 - Améliorations (À venir)
- [ ] Dashboard utilisateur amélioré
- [ ] Graphiques de progression
- [ ] Comparaison de builds
- [ ] Analyse de guilde avancée
- [ ] Export CSV/JSON

### v5.0 - Social (Futur)
- [ ] Login GitHub OAuth
- [ ] Partage public de rapports
- [ ] Classements communautaires
- [ ] API publique
- [ ] Bot Discord
- [ ] Historique des matchups serveur

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
