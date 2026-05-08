# TSFA — Prompt de démarrage pour IA de coding
> À utiliser avec Claude Code, Cursor, Aider, ou tout coding agent.
> Placer ce fichier dans ~/tsfa/ et l'exécuter depuis ce répertoire.

---

## PROMPT

Tu es un ingénieur backend senior Python spécialisé en APIs ML et MLOps.
Tu travailles sur le projet **TSFA (Time Series Forecasting API)**, une API B2D
commerciale destinée à être publiée sur RapidAPI puis AWS Marketplace.

Commence par lire **intégralement** les deux fichiers suivants avant d'écrire
la moindre ligne de code :

- `project-context.md` — stratégie, positionnement, modèle économique
- `project-specs.md`   — architecture, endpoints, schemas, stack, roadmap

---

## CONTEXTE ENVIRONNEMENT

Tu travailles directement sur un VPS Hetzner (Ubuntu 24.04, CX22).
- Répertoire racine du projet : `~/tsfa/`
- Docker et Docker Compose sont installés et fonctionnels
- Caddy est installé (reverse proxy + HTTPS)
- Git est initialisé dans ce répertoire
- L'inférence ML lourde sera déléguée à Modal.com (GPU serverless)
- Pour la Phase 1 MVP, on utilise d'abord **statsforecast (AutoARIMA)** en local
  sans GPU, pour valider l'architecture avant d'intégrer Modal + Chronos

---

## CE QUE TU DOIS CONSTRUIRE — PHASE 1 UNIQUEMENT

Implémente strictement la **Semaine 1 du roadmap** défini dans `project-specs.md` :

### 1. Structure complète du projet
Crée **tous** les dossiers et fichiers vides avec la structure définie dans la
section "4. Structure du projet" des specs. Chaque fichier doit exister, même
s'il est vide ou contient juste un placeholder.

### 2. Configuration Docker
- `Dockerfile` pour l'app FastAPI (base image `python:3.11-slim`)
- `docker-compose.yml` avec les services : `api`, `redis`
- `.env.example` complet avec toutes les variables définies dans les specs
- `.env` local pré-rempli avec des valeurs de développement (Redis local, debug=true)
- `.dockerignore` propre

### 3. Application FastAPI — fondations
- `app/main.py` : setup complet de l'app (CORS, lifespan, routers montés,
  middleware logging, handler d'erreurs global)
- `app/config.py` : Settings Pydantic-settings lisant depuis `.env`
- `app/dependencies.py` : dépendance `get_plan()` qui lit le header
  `X-RapidAPI-User` et retourne le plan (free/basic/pro/ultra) —
  en Phase 1 on simule avec un header `X-Plan` pour les tests locaux

### 4. Schemas Pydantic complets
Implémente **tous** les schemas request/response définis dans les specs :
- `app/schemas/forecast.py` : UnivariateForecastRequest, MultivariateForecastRequest,
  BatchForecastRequest, ForecastResponse, ForecastResult, Diagnostics, Meta
- `app/schemas/validate.py` : ValidateRequest, ValidateResponse, BacktestMetrics
- `app/schemas/common.py` : ErrorResponse, UsageResponse, ModelInfo

Les schemas doivent inclure :
- Validators Pydantic v2 (`@field_validator`, `model_validator`)
- Exemples OpenAPI (`model_config = ConfigDict(json_schema_extra={"example": {...}})`)
- Toutes les contraintes (min/max length, allowed values, etc.)

### 5. Endpoint `/forecast/univariate` — fonctionnel de bout en bout
C'est le seul endpoint qui doit réellement fonctionner en Phase 1 :
- `app/routers/forecast.py` : route POST `/v1/forecast/univariate`
- `app/services/forecaster.py` : logique d'orchestration
- `app/services/model_selector.py` : fonction `select_model()` telle que définie
  dans les specs (section 6)
- `ml/models/arima_model.py` : wrapper AutoARIMA via `statsforecast`
  — c'est le seul modèle actif en Phase 1
- `ml/preprocessing/cleaner.py` : pipeline complet (missing values, type check,
  length validation)
- `ml/preprocessing/frequency_detector.py` : détection auto de fréquence
- `ml/postprocessing/diagnostics.py` : calcul trend, détection saisonnalité basique
- `ml/postprocessing/confidence.py` : calcul intervalles de confiance depuis
  les résidus statsforecast

La réponse doit être **exactement** conforme au schema de réponse défini dans
les specs (section 2.1), incluant `diagnostics` et `meta.inference_time_ms`.

### 6. Autres endpoints — stubs documentés
Les endpoints suivants doivent exister et retourner une réponse `501 Not Implemented`
propre avec un message `"Coming in Phase 2"` :
- `POST /v1/forecast/multivariate`
- `POST /v1/forecast/batch`
- `POST /v1/validate`

### 7. Endpoints utilitaires — fonctionnels
- `GET /v1/models` : retourne la liste statique des modèles (section 2.5 des specs)
  avec `available: true` uniquement pour `arima` en Phase 1
- `GET /v1/usage` : retourne des données mockées (credits_used: 0)
- `GET /health` : `{"status": "ok", "version": "1.0.0"}`

### 8. Middleware & error handling
- `app/middleware/logging.py` : log structuré (structlog) de chaque requête
  avec `request_id`, méthode, path, status_code, durée en ms
- `app/middleware/error_handler.py` : handler global qui transforme toutes les
  exceptions en `ErrorResponse` JSON avec les codes définis dans les specs

### 9. Cache Redis
- Dans `app/services/forecaster.py` : avant chaque inférence, vérifie si une
  réponse identique est en cache Redis (clé = hash SHA256 du payload)
  TTL = 900 secondes (15 minutes)

### 10. Tests
- `tests/unit/test_schemas.py` : tests de validation Pydantic (cas valides,
  cas invalides, edge cases)
- `tests/unit/test_model_selector.py` : tests de la logique de sélection
- `tests/integration/test_forecast_endpoint.py` : tests du endpoint univarié
  avec `httpx` et `TestClient` FastAPI — au moins 5 cas : succès, série trop
  courte, horizon invalide, fréquence invalide, modèle inconnu

### 11. Fichiers de config infra
- `infra/nginx.conf` : non utilisé en Phase 1 (on utilise Caddy) mais préparé
- `infra/prometheus.yml` : scrape config pour l'app FastAPI
- `Caddyfile` à la racine : config pour `api.tsfa.io` → proxy vers `localhost:8000`
  (laisse le domaine en placeholder si pas encore configuré)

### 12. Documentation développeur minimale
- `README.md` complet : description du projet, prérequis, installation locale
  (`docker-compose up`), variables d'environnement, exemples curl
- `docs/quickstart.md` : guide 5 minutes pour un développeur externe
- `docs/examples/python_example.py` : exemple complet avec commentaires
- `docs/examples/curl_example.sh` : 3 exemples curl commentés

---

## CONTRAINTES STRICTES

**Ne pas faire :**
- ❌ Ne pas intégrer Modal.com maintenant (Phase 2)
- ❌ Ne pas intégrer Chronos, LSTM, TiDE maintenant (Phase 2)
- ❌ Ne pas implémenter le billing Stripe maintenant (Phase 2)
- ❌ Ne pas créer de frontend ou dashboard
- ❌ Ne pas inventer de fonctionnalités non définies dans les specs

**Toujours faire :**
- ✅ Typage Python strict partout (type hints complets)
- ✅ Docstrings sur chaque fonction publique
- ✅ Gestion d'erreurs explicite (pas de `except: pass`)
- ✅ Logs structurés sur les opérations importantes
- ✅ Variables de config lues depuis `.env` via `config.py`, jamais hardcodées
- ✅ Code prêt pour la production (pas de TODO bloquants)
- ✅ `requirements.txt` avec versions pinnées

---

## ORDRE D'EXÉCUTION

Procède dans cet ordre exact, en validant chaque étape avant de passer à la suivante :

1. Crée la structure de dossiers complète
2. Installe les dépendances (`pip install` ou via Docker)
3. Implémente les schemas Pydantic + teste leur validation
4. Implémente le preprocessing pipeline + teste avec des séries synthétiques
5. Implémente le modèle AutoARIMA + teste en isolation
6. Câble le tout dans le service forecaster
7. Implémente les routes FastAPI + middleware
8. Lance l'app (`docker-compose up`) et teste manuellement avec curl
9. Lance les tests automatisés (`pytest`)
10. Vérifie que `GET /health` et `POST /v1/forecast/univariate` fonctionnent
    de bout en bout avec une vraie série de test

---

## COMMANDE DE VALIDATION FINALE

À la fin, l'exécution de cette commande doit retourner une réponse JSON valide
et complète conforme aux specs :

```bash
curl -X POST http://localhost:8000/v1/forecast/univariate \
  -H "Content-Type: application/json" \
  -H "X-Plan: free" \
  -d '{
    "series": [120, 132, 128, 145, 139, 152, 148, 160, 155, 168, 163, 175],
    "horizon": 7,
    "frequency": "D",
    "model": "auto"
  }'
```

Réponse attendue : JSON avec `status: "success"`, `forecast.mean` (array de 7 valeurs),
`forecast.lower_95`, `forecast.upper_95`, `diagnostics`, et `meta.inference_time_ms`.

**Le projet est prêt quand ce curl fonctionne et que `pytest` passe au vert.**
