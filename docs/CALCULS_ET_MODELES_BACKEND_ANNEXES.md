# Annexes — Agrégation multi-fights et contrôles transverses

Ces annexes complètent « CALCULS_ET_MODELES_BACKEND.md » avec des détails opérationnels sur:
- Annexe A: Agrégation multi-fights (analyse_multiple_files)
- Annexe B: Contrôles transverses (rate limiting, validation ZIP)


## Annexe A — Agrégation multi-fights
Référence: services/analysis_service.py::analyze_multiple_files

Objectif: traiter un lot de fichiers EVTC/ZEVTC et produire une synthèse globale exploitable par l’UI et le moteur de reco.

- Entrée
  - Liste de fichiers validés `(filename, content)`.
  - Chaque fichier est analysé: d’abord via dps.report (si disponible), sinon fallback sur le parseur local.

- Compteurs globaux
  - `total_fights`: nombre de fichiers traités avec succès
  - `victories`, `defeats`, `draws`: décomptes sur les issues par fight
  - `total_duration_sec`: somme des durées

- Joueurs uniques (alliés)
  - Ensemble `unique_players` construit à partir des comptes alliés inclus en squad (`in_squad == True`).

- Agrégations alliés (par `account`)
  - Sommes: `damage`, `kills`, `deaths`, `downs`
  - `fight_count`: nombre de fights dans lesquels l’allié apparaît
  - Conserve `profession`, `role`, `group` (le dernier observé)

- Agrégations ennemis (par `name`)
  - Sommes: `damage_taken`
  - `fight_count`: nombre d’occurrences

- Compositions cumulées
  - Alliés: `ally_spec_counts`, `ally_role_counts` (sommes sur tous les fights)
  - Ennemis: `enemy_spec_counts`, `enemy_role_counts` (sommes sur tous les fights)

- Détails par rôle
  - Alliés: `ally_specs_by_role[role][spec] += 1` à partir des agrégats alliés
  - Ennemis: `enemy_specs_by_role[role][spec] += 1` à partir des agrégats ennemis

- Statistiques de fight cumulées
  - `total_ally_deaths`, `total_ally_kills`, `total_ally_damage`, `total_ally_downs`

- Détail par fight
  - `per_fight_enemy_breakdown`: pour chaque fight, `fight_number`, `filename`, `role_counts` ennemis, `total_enemies`

- Issue globale de la session
  - `victory` si `victories > defeats`, `defeat` si l’inverse, sinon `draw`

- Sortie
  - `aggregated_players`: structure prête pour l’UI (alliés/ennemis agrégés, compositions, stats, durée)
  - `summary`: récapitulatif haut-niveau
  - `ai_counter`: recalculé sur `total_enemy_spec_counts`

Exemple minimal (3 fights)
- Issues: 2 victoires, 1 défaite → overall `victory`
- Sommes alliées: damage=3.2M, kills=28, deaths=19, downs=24
- `enemy_spec_counts` total: {Firebrand: 6, Scrapper: 5, Scourge: 9, Spellbreaker: 7}
- Reco recalculée sur cette composition totale ennemie


## Annexe B — Contrôles transverses
Références: rate_limiter.py, services/file_validator.py (et implémentation équivalente dans main.py)

Rate limiting (upload)
- Modèle: in-memory par IP, fenêtre glissante `window_seconds=60`, `max_requests=10`
- API: `check_upload_rate_limit(request)`
- Détails: nettoyage périodique (`cleanup_old_entries`) et verrou asynchrone (`asyncio.Lock`)
- Erreur: 429 si dépassement de quota

Validation de fichiers/ZIP
- Extensions autorisées: `.evtc`, `.zevtc`, `.zip`
- Taille maximale: 50MB (413 si dépassement)
- Fichier non vide requis
- Règles spécifiques ZIP:
  - ≤ 100 fichiers dans l’archive
  - Pas de chemins dangereux (préfixe `/` ou `..`)
  - Contenu strictement `.evtc` ou `.zevtc`
  - Taille décompressée ≤ 100MB (2× la limite par fichier)
- Erreurs typiques (400): type interdit, ZIP corrompu, zip bomb, chemins invalides
- Emplacements d’usage:
  - routers/analysis.py → `services/file_validator.validate_upload_file`
  - main.py → version locale équivalente pour l’endpoint direct

Exemples
- `report.zevtc` de 60MB → 413 « File too large »
- `logs.zip` avec 110 entrées → 400 « ZIP contains too many files (max 100) »
- `logs.zip` contenant `readme.txt` → 400 « ZIP must only contain .evtc or .zevtc files »
