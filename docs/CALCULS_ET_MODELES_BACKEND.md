# GW2 CounterPicker — Documentation des calculs et modèles du backend

Cette documentation décrit précisément tous les calculs, heuristiques et agrégations utilisés côté backend, leurs objectifs, ainsi que des exemples concrets. Les références incluent le chemin des fichiers et le nom des fonctions.


## Sommaire
- Présentation globale et objectifs
- Parsing EVTC et extraction des métriques (parser.py)
- Détection du rôle/build et confiance (parser.py, role_detector.py)
- Classification WvW vs PvE (main.py::is_wvw_log)
- Détection du contexte de combat (services/counter_service.py::guess_fight_context)
- Déduplication des combats et empreinte (fingerprint)
- Détermination de l’issue du combat (analysis_service.py, counter_service.py)
- Enregistrement et score de performance des builds (services/counter_service.py::_store_build_performance)
- Similarité de compositions (services/counter_service.py::_calculate_composition_similarity)
- Recherche de combats similaires et décroissance temporelle (services/counter_service.py::_find_similar_fights)
- Analyse des besoins tactiques ennemis (services/counter_service.py::_analyze_enemy_needs)
- Sélection des meilleurs builds (winrate, feedback) (services/counter_service.py::get_best_builds_against)
- Composition recommandée avec couverture des rôles (services/counter_service.py::get_best_builds_with_role_coverage)
- Calcul du niveau de confiance de la recommandation (services/counter_service.py::_calculate_confidence)
- Étiquettes « meta » lisibles (services/counter_service.py::_get_meta_tags)
- Moteur « rule-based » complémentaire (counter_engine.py)
- Statut et métriques globales (services/counter_service.py::get_status)
- Limitations et paramètres
 - Annexe A — Agrégation multi-fights (services/analysis_service.py::analyze_multiple_files)
 - Annexe B — Contrôles transverses (rate limiting, validation ZIP)


## Présentation globale et objectifs
Le backend combine:
- Un parseur EVTC réel pour extraire des métriques par joueur (dégâts, cleanses, strips, etc.).
- Des heuristiques pour détecter rôles/builds, contexte du fight, issue, besoins tactiques.
- Un moteur de recommandation statistiques+heuristiques basé sur l’historique (TinyDB): winrates par (spec, rôle) contre des compositions ennemies similaires, agrégations de performance et retour utilisateur (feedback).

Objectif: recommander des contres et une composition optimale selon la compo ennemie observée et le contexte (zerg, raid de guilde, roam), avec un niveau de confiance explicite.


## Parsing EVTC et extraction des métriques
Fichier: parser.py (classes EVTCParser, RealEVTCParser)

- Extraction d’événements combat et agrégation par joueur:
  - Dégâts directs: somme des `value` avec filtres (0 < value < 500000) et `buff == 0`.
  - Dégâts d’altérations: somme des `buff_dmg` avec filtres (0 < buff_dmg < 500000) et `buff == 1`.
  - Strips de boons: `buff == 1` et `is_buffremove == 1` sur un ennemi → `boon_strips += 1`.
  - Cleanses: `buff == 1` et `is_buffremove == 2` avec ID d’altération connu → `cleanses += 1`.
  - CC/interruptions: `result == 5` → `cc_out += 1`.
  - Kills: `result == 8` (killing blow) → `kills += 1`.
  - Barrier: `is_shields` et `value > 0` → `barrier_out += value`.
  - Suivi de compétences utilisées, boons/conditions appliqués (via listes d’IDs).

- Détection alliés/ennemis: mélange team_id, sous-groupe et patterns de dégâts échangés.

- Durée: `duration_ms = end_time - start_time`, dérivée d’événements d’état (ou fallback selon activité).

Exemple rapide: si un joueur a 220k dégâts directs, 80k dégâts d’altérations, 12 strips, 25 cleanses, 3 kills et 1 interruption, ces compteurs sont stockés dans `ParsedPlayer` et utilisés plus tard pour rôle/build et scoring.


## Détection du rôle/build et confiance
Fichiers: parser.py::_detect_role_and_build, role_detector.py

- Rôle par défaut selon la spécialisation (mappage `ROLE_DETECTION` côté parser, ou via sets côté role_detector: `STAB_SPECS`, `HEALER_SPECS`, `BOON_SPECS`, `STRIP_DPS_SPECS`).
- Raffinements (parser.py):
  - Support si forte sortie de Quickness/Alacrity (`quickness_applied > 50` ou `alacrity_applied > 50`).
  - Heuristiques de build (ex: Firebrand: Quickbrand si Quickness élevé, Healbrand si `healing_power > 1000`).
- Détection avancée côté role_detector.py (non systématiquement utilisée partout):
  - Normalisation par durée et seuils: `healing_per_sec >= 800` → healer, `stab_gen >= 5.0` → stab, `strips_per_min >= 20` → dps_strip, etc.
- Confiance de l’inférence de build (parser): `confidence = min(99.0, 50.0 + 2 * data_points)` où `data_points = len(skills_used) + len(boons_applied) + len(conditions_applied)`.

Exemple: un Scrapper avec `healing_power=900`, `alacrity_applied=0`, `quickness_applied=0`, beaucoup de cleanses → rôle « Support », build « Heal Scrapper » et, s’il a 40 skills + 10 boons + 8 conditions observés, `confidence ≈ min(99, 50 + 2*(58)) = 99`.


## Classification WvW vs PvE
Fichier: main.py::is_wvw_log

Heuristique de filtrage des rapports EI (dps.report):
- Rejette si `triggerID`/boss/CM correspond à des combats PvE connus (listes d’IDs, CM vrais, golems, noms d’instances PvE).
- Accepte si la cible contient des `enemyPlayer: true`.
- Fallback prudents si cibles vides.

Exemple: si `fightName` contient « Dhuum » ou `triggerID` est dans la liste raids, le log est rejeté (PvE).


## Détection du contexte de combat
Fichier: services/counter_service.py::guess_fight_context

Règles (ordre simplifié):
- Roam: `ally_count <= 10` et `enemy_count <= 12`.
- Zerg: `ally_count >= 25` ou `enemy_count >= 30`.
- Guild Raid: `10 <= ally_count <= 25` et (`main_guild_ratio >= 0.5` ou `subgroup_count >= 2`).
- Ambigus: si `10 <= ally_count <= 25` et `enemy_count >= 20` → Zerg sinon Unknown.

Exemple: 18 alliés, 22 ennemis, 3 sous-groupes → Guild Raid. 18 alliés, 22 ennemis, 1 sous-groupe → Zerg (ambigu dans la tranche, règle spéciale).


## Déduplication des combats et empreinte (fingerprint)
Fichier: services/counter_service.py::generate_fight_fingerprint

Empreinte MD5 des éléments concaténés:
- `duration_bucket = floor(duration_sec / 5) * 5`
- `ally_accounts_hash` = concat des noms de comptes alliés (triés, tronqués, top 10)
- `ally_specs_hash` = concat des specs alliées triées
- `damage_bucket = floor(total_ally_damage / 50000) * 50000`

But: refuser les doublons exacts depuis la même perspective. Les empreintes sont conservées (table `fight_fingerprints`) avec nettoyage périodique (`cleanup_old_fingerprints(days=7)`).

Exemple: `180s | [10 comptes] | [ally_specs triées] | 350000` → MD5 → `abcd1234ef567890` (16 chars).


## Détermination de l’issue du combat
Fichiers: analysis_service.py::determine_fight_outcome et services/counter_service.py::record_fight

- Variante courte (analysis_service):
  - Si durée < 30s: victoire si 0 morts alliés et ennemis > 0; défaite si morts alliées > 50% de l’effectif, sinon nul.
  - Sinon: `death_ratio = ally_deaths / allies`; victoire si `< 0.2`, défaite si `> 0.6`, sinon nul.

- Variante lors de l’enregistrement (record_fight) quand outcome « unknown »:
  - Si `ally_kills > 0` et `ally_deaths == 0` → victory.
  - Sinon `ally_kills > ally_deaths` → victory.
  - Sinon `ally_deaths > ally_kills * 2` et `ally_deaths >= 3` → defeat.
  - Sinon `ally_deaths > ally_kills` et `ally_deaths >= 5` → defeat.
  - Sinon → draw.

Exemple: 6 kills alliés, 2 morts alliées → victory. 1 kill, 4 morts → defeat. 2 vs 3 morts → draw.


## Enregistrement et score de performance des builds
Fichier: services/counter_service.py::_store_build_performance

Score par build (avant clamp et pénalité morts):
- `role == 'healer'`: `score = healing + 10 * cleanses`.
- `role == 'stab'`: `score = 100 * sum(boon_gen.values())`.
- `role == 'dps_strip'`: `score = dps + 50 * boon_strips`.
- sinon (DPS générique): `score = dps + 2 * down_contrib`.
- Pénalité: `score = max(0, score - 5000 * deaths)`.

Exemple: Healer: `healing=300000`, `cleanses=80`, `deaths=1` → `300000 + 800 - 5000 = 295800`.


## Similarité de compositions (pondérée par rôle)
Fichier: services/counter_service.py::_calculate_composition_similarity

Définitions:
- Poids de rôle: `stab=2.0`, `healer=1.8`, `boon=1.5`, `strip=1.3`, `dps=1.0`.
- Distance Manhattan pondérée: `D = Σ_spec |c1 - c2| * w(spec)`.
- Normalisation: `W = Σ_spec max(c1, c2) * w(spec)`.
- Similarité: `sim = 1 - D / (2W)`, bornée à `[0, 1]`.

Exemple: comp1 `{Firebrand:3, Scourge:4, Spellbreaker:2}` vs comp2 `{Firebrand:2, Scourge:5, Vindicator:1}`.
- Poids: Firebrand=2.0 (stab), Scourge=1.3 (strip), Spellbreaker=1.3 (strip), Vindicator=1.8 (healer).
- `D = |3-2|*2.0 + |4-5|*1.3 + |2-0|*1.3 + |0-1|*1.8 = 2.0 + 1.3 + 2.6 + 1.8 = 7.7`.
- `W = 3*2.0 + 5*1.3 + 2*1.3 + 1*1.8 = 6 + 6.5 + 2.6 + 1.8 = 16.9`.
- `sim = 1 - 7.7/(2*16.9) ≈ 0.772`.


## Recherche de combats similaires et décroissance temporelle
Fichier: services/counter_service.py::_find_similar_fights

- Filtre par contexte si fourni (`zerg`, `guild_raid`, `roam`).
- Garde les combats avec `similarity >= 0.3`.
- Pondération temporelle (jours écoulés): `<=7:1.0`, `<=30:0.9`, `<=60:0.7`, `<=90:0.5`, `>90:0.3`.
- Score final de pertinence: `final_score = similarity * time_weight`.

Exemple: `sim=0.72` et combat vieux de 45 jours → `time_weight=0.7`, `final=0.504`.


## Analyse des besoins tactiques ennemis
Fichier: services/counter_service.py::_analyze_enemy_needs

Variables:
- Comptes par rôles ennemis via sets (role_detector): `enemy_stab_count`, `enemy_healer_count`, `enemy_boon_count`, et count spécifique des `Scourge/Harbinger` pour la pression alté.
- Ratios: `stab_ratio = enemy_stab_count / total`, etc.

Scores (bornés à `[0,1]`):
- `strip = min(1, 1.5 * (stab_ratio + boon_ratio))`.
- `heal = min(1, 0.3 + 1.2 * condi_ratio + 0.5 * healer_ratio)`.
- `stab = min(1, 0.4 + enemy_scourge_count / total)`.
- `boon = min(1, 0.4 + 0.8 * (healer_ratio + stab_ratio))`.
- `burst = min(1, 0.5 + 1.0 * (healer_ratio + stab_ratio))`.

Exemple: `{Firebrand:3, Scrapper:2, Scourge:4, Spellbreaker:2}` (total=11)
- `stab_ratio=3/11≈0.273`, `healer_ratio=2/11≈0.182`, `boon_ratio=0`, `condi_ratio=4/11≈0.364`.
- `strip≈0.41`, `heal≈0.83`, `stab≈0.76`, `boon≈0.76`, `burst≈0.95`.


## Sélection des meilleurs builds (winrate, feedback)
Fichier: services/counter_service.py::get_best_builds_against

Étapes:
1) Filtrage par contexte (si fourni) et similarité Jaccard sur les sets de specs ennemies: `sim_jaccard = |S∩B|/|S∪B| ≥ 0.3`.
2) Agrégation par clé `(spec, role)`:
   - `wins`, `total` (victoires/décomptes), 
   - moyennes: `avg_dps`, `avg_healing`, `avg_strips`, `avg_cleanses`, `avg_score`.
   - `counts_in_wins[fight_id]` = combien de fois ce `(spec, role)` était présent dans les fights gagnés.
3) Winrate: `win_rate = round(100 * wins / total, 1)`.
4) Ajustement par feedback utilisateur (si dispo) pour la compo ennemie:
   - `factor = 1 + feedback_weight * (fb_rate - 0.5)` (par défaut `feedback_weight=0.35`).
   - `win_rate = clamp(win_rate * factor, 0, 100)`.
5) `recommended_count` = arrondi de la moyenne de `counts_in_wins` (min 1).
6) Meilleur par rôle: max `win_rate`, bris d’égalité par `avg_score`.

Exemples:
- Jaccard: S ennemi `{FB, Scourge, SB}` vs B `{Scourge, Herald, Tempest, FB, Chrono}` → `|∩|=2`, `|∪|=6` → `0.333` (conservé).
- Feedback: `win_rate=65`, `fb_rate=0.70`, `feedback_weight=0.35` → `factor=1+0.35*(0.2)=1.07` → `69.55` → `69.6`.


## Composition recommandée avec couverture des rôles
Fichier: services/counter_service.py::get_best_builds_with_role_coverage

- Base: `best_by_role = get_best_builds_against(...)`.
- Score par spec:
  - `base_score = win_rate / 100`.
  - `coverage_score` = somme des besoins couverts pondérés: 
    - `+ 0.3 * needs['stab']` si spec ∈ STAB_SPECS
    - `+ 0.3 * needs['heal']` si spec ∈ HEALER_SPECS
    - `+ 0.25 * needs['boon']` si spec ∈ BOON_SPECS
    - `+ 0.25 * needs['strip']` si spec ∈ STRIP_DPS_SPECS
    - `+ 0.2 * needs['burst']` si spec ∈ {Willbender, Vindicator, Bladesworn}
  - `final_score = 0.6 * base_score + 0.4 * coverage_score`.
- Allocation d’emplacements (heuristique): supports (stab/heal) 2–3, boon 2, dps jusqu’à 4, en respectant `squad_size` et l’ordre de `final_score`.

Exemple: `needs` de l’exemple précédent et `Spellbreaker` avec `win_rate=70`.
- `base=0.70`, `coverage≈0.25*strip(0.41)=0.103` → `final≈0.6*0.70 + 0.4*0.103 ≈ 0.461`.


## Calcul du niveau de confiance de la recommandation
Fichier: services/counter_service.py::_calculate_confidence

Facteurs [0–1] et poids:
- `data_quantity` (0.35): basé sur le nombre de fights similaires (seuils: 2,5,10,20).
- `data_quality` (0.25): variance des `win_rate` des meilleurs builds (faible variance → haute qualité).
- `consistency` (0.25): min `fights_played` parmi les builds recommandés (seuils: 3,5).
- `recency` (0.15): ratio de fights ≤ 30 jours.

`overall = 0.35*qte + 0.25*qual + 0.25*cons + 0.15*recency`, converti en `%` et catégorisé: ≥80 Élevée, ≥60 Moyenne, sinon Faible.

Exemple: `similar_fights=12` → `qte=0.8`; `win_rates=[68,72,70]` → variance ~2.7 → `qual=1.0`; `min_fights=4` → `cons=0.7`; `recency=6/12=0.5`.
- `overall=0.35*0.8 + 0.25*1.0 + 0.25*0.7 + 0.15*0.5 = 0.78` → `78%` (Moyenne).


## Étiquettes « meta » lisibles
Fichier: services/counter_service.py::_get_meta_tags

- Basées sur `needs`:
  - `strip > 0.7` → « Beaucoup de boons »
  - `heal > 0.7` → « Beaucoup d’altérations »
  - `burst > 0.7` → « Beaucoup de supports »
- Taille: `total <= 10` → « Petit groupe » ; `total >= 30` → « Gros blob ».


## Moteur « rule-based » complémentaire
Fichier: counter_engine.py

- Relations `COUNTERS` (qui contre quoi) et `ROLE_COUNTERS` (quels rôles contre quels rôles).
- Score par spec = somme des poids par occurrences d’ennemis contrés (specs et rôles), puis tri.
- Recommandations de builds avec URLs (metabattle) et notes de stratégie selon `estimated_squad_type`.
- Confiance (simple): `confidence = min(95, 60 + 2 * len(enemy_comp.spec_counts))`.

Remarque: Le service stats-based (CounterService) est prioritaire pour la recommandation; le moteur rule-based sert de base/complément.


## Statut et métriques globales
Fichier: services/counter_service.py::get_status

- `total_fights`: nombre de fights avec compo.
- `win_rate`: global (victoires/total).
- `unique_players`: comptes uniques vus.
- `last_updated`, `engine`.


## Limitations et paramètres
- Heuristiques dépendantes de la meta: les sets `STAB_SPECS`, `HEALER_SPECS`, etc. doivent être maintenus.
- Données partielles: côté ennemis, souvent seuls les noms de spé sont connus → rôle estimé.
- Seuils arbitraires mais explicités (ex: Jaccard 0.3, variance winrate < 100, pénalité 5000/death, buckets durée/50000 dmg, time decay par paliers).
- Paramètre `feedback_weight` (par défaut 0.35) ajustable via `settings_table`.
- Déduplication: fingerprint ≈ collision faible mais possible si mêmes 4 champs regroupés.


## Glossaire
- strip: retrait de boons sur ennemis
- cleanse: retrait d’altérations sur alliés
- stab: stabilité
- boon: avantages (quickness/alacrity/might/etc.)
- Jaccard: |intersection| / |union| de deux ensembles
- Manhattan pondérée: somme pondérée des différences absolues


## Exemples d’usage intégrés (end-to-end)
1) Upload EVTC → parse → players_data → record_fight:
   - Issue calculée, compo ennemie agrégée, empreinte anti-dup, stats globales mises à jour, historiques par build enregistrés.
2) Recalcul d’un contre pour une compo ennemie donnée:
   - `similar_fights` via similarité pondérée + time decay
   - `best_builds` via winrates/feedback
   - `needs` → `meta_tags`
   - `get_best_builds_with_role_coverage` → compo complète
   - `_calculate_confidence` → score/confiance.

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
