# GW2 CounterPicker - Roadmap vers 10/10

## ✅ Améliorations Complétées (Note actuelle: 7.5/10)

### UX/UI
1. **Unification Analyser/Soirée** ✅
   - Une seule page `/analyze` avec support multi-fichiers
   - Drag & drop pour 1 ou plusieurs fichiers
   - Redirection automatique de `/evening` vers `/analyze`

2. **Bouton Feedback** ✅
   - Ajouté dans la navigation principale
   - Lien mailto pour faciliter les retours utilisateurs

3. **Couleurs par groupe (1-10)** ✅
   - Support complet pour 10 groupes au lieu de 5
   - Couleurs distinctives pour chaque groupe

4. **Réorganisation des onglets** ✅
   - Combat en premier
   - Down Contrib déplacé vers Dégâts

5. **Simplification Boons** ✅
   - Toggle pour afficher/masquer boons secondaires
   - Stab affiché en stacks au lieu de %

6. **CC reçus** ✅
   - Ajouté dans l'onglet Défensif

## 🚧 Améliorations en Cours (Priorité Haute)

### UX/UI Restantes
1. **Tri cliquable sur colonnes**
   - Supprimer boutons "Trier: Classe, Groupe, Rôle"
   - Rendre toutes les colonnes triables au clic
   - Impact: Améliore significativement l'ergonomie

2. **Améliorer IA Vivante**
   - Clarifier "Contre-composition recommandée"
   - Améliorer présentation "Composition ennemie analysée"
   - Impact: Meilleure compréhension de l'IA

### Sécurité (Critique)
3. **Sécuriser les uploads**
   - Limite de taille: 50MB par fichier
   - Rate limiting: 10 requêtes/minute
   - Validation contenu ZIP
   - Nettoyage fichiers temporaires
   - Impact: Évite abus et surcharge serveur

### Architecture (Important)
4. **Logging structuré**
   - Remplacer print() par logging
   - Logs avec niveaux (INFO, WARNING, ERROR)
   - Rotation des logs
   - Impact: Meilleur debugging et monitoring

5. **Scinder main.py**
   - Créer routers/ pour les routes
   - Créer services/ pour la logique métier
   - Séparer configuration
   - Impact: Maintenabilité et scalabilité

### Qualité (Important)
6. **Tests unitaires**
   - pytest pour les fonctions critiques
   - Tests du parser
   - Tests des endpoints API
   - Impact: Fiabilité et non-régression

## 📋 Améliorations Futures (Moyen Terme)

### Performance
- Cache Redis pour les résultats
- Parsing asynchrone avec queue
- Compression des réponses
- CDN pour les assets statiques

### Base de données
- Migration TinyDB → PostgreSQL
- Connexions poolées
- Migrations avec Alembic
- Backup automatique

### Monitoring
- Prometheus + Grafana
- Health checks
- Alerting
- Métriques temps réel

## 🎯 Estimation Impact sur la Note

| Amélioration | Impact Note | Effort |
|-------------|-------------|--------|
| Tri cliquable | +0.3 | Faible |
| Améliorer IA Vivante | +0.2 | Faible |
| Sécuriser uploads | +0.8 | Moyen |
| Logging structuré | +0.4 | Faible |
| Scinder main.py | +0.5 | Moyen |
| Tests unitaires | +0.8 | Élevé |

**Note cible avec améliorations prioritaires: 9.5/10**
**Note cible avec tous les changements: 10/10**

## 📝 Notes Techniques

### Réponses aux questions utilisateur

**Q: Stab en stacks = uptime moyen ?**
R: Oui, les stacks représentent l'uptime moyen de Stability. C'est calculé comme la moyenne pondérée des stacks actifs sur la durée du combat.

**Q: Mot de passe SSH automatique ?**
R: Pour des raisons de sécurité, je ne peux pas stocker le mot de passe. Solution recommandée: configurer une clé SSH pour éviter les prompts.

### Architecture Recommandée

```
gw2-counterpicker/
├── app/
│   ├── __init__.py
│   ├── main.py (FastAPI app)
│   ├── config.py (Configuration)
│   ├── routers/
│   │   ├── analyze.py
│   │   ├── meta.py
│   │   └── ai.py
│   ├── services/
│   │   ├── parser_service.py
│   │   ├── ai_service.py
│   │   └── storage_service.py
│   ├── models/
│   │   └── schemas.py
│   └── utils/
│       ├── logging.py
│       └── security.py
├── tests/
│   ├── test_parser.py
│   ├── test_api.py
│   └── test_ai.py
├── requirements.txt
├── requirements-dev.txt
└── pytest.ini
```

## 🚀 Prochaines Étapes Immédiates

1. Implémenter tri cliquable (30 min)
2. Améliorer UI IA Vivante (30 min)
3. Sécuriser uploads (1h)
4. Ajouter logging (1h)
5. Déployer et tester (30 min)

**Temps total estimé: 3.5 heures**
