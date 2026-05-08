# project-specs.md
> Spécifications techniques complètes — API B2D : Time Series Forecasting
> Phase 1 — MVP RapidAPI | Auteur : Dorian Marty | Version : 1.0

---

## 0. Vue d'ensemble du projet

**Nom de code :** `TSFA` — Time Series Forecasting API  
**Objectif :** Exposer une API REST de prédiction de séries temporelles professionnelle, benchmarkée, consommable en 3 lignes de code depuis n'importe quel langage.  
**Cible Phase 1 :** Publication sur RapidAPI avec plans freemium → payants.  
**Cible Phase 2 :** Migration / duplication sur AWS Marketplace SaaS.  
**Revenue model :** Abonnement mensuel par tier de volume.

---

## 1. Architecture globale

```
┌─────────────────────────────────────────────────────────────┐
│                        CLIENT (dev)                          │
│         curl / Python / JS / n'importe quel langage          │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTPS + API Key
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    RAPIDAPI GATEWAY                          │
│         Rate limiting | Auth | Billing | Analytics           │
└──────────────────────────┬──────────────────────────────────┘
                           │ forwarded request
                           ▼
┌─────────────────────────────────────────────────────────────┐
│               FASTAPI ROUTING LAYER                          │
│  Hetzner VPS (2 vCPU / 4GB RAM / Ubuntu 24)                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │ /forecast│  │ /detect  │  │ /validate│  │ /benchmark │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └─────┬──────┘  │
│       │              │              │               │         │
│  Pydantic validation + schema enforcement + error handling   │
└──────────────────────────┬──────────────────────────────────┘
                           │ async job dispatch
                           ▼
┌─────────────────────────────────────────────────────────────┐
│               ML INFERENCE LAYER (Modal.com)                 │
│  GPU on-demand — facturation à l'usage (0€ si 0 requête)    │
│                                                              │
│  ┌─────────────────┐     ┌─────────────────────────────┐    │
│  │  Model Registry  │     │      Inference Workers       │    │
│  │                  │     │                              │    │
│  │  • Chronos-T5    │────▶│  univariate_forecaster.py   │    │
│  │  • TiDE          │     │  multivariate_forecaster.py │    │
│  │  • LSTM custom   │     │  ensemble_forecaster.py     │    │
│  │  • Fallback ARIMA│     │                              │    │
│  └─────────────────┘     └─────────────────────────────┘    │
└──────────────────────────┬──────────────────────────────────┘
                           │
          ┌────────────────┴──────────────────────┐
          ▼                                        ▼
┌─────────────────┐                   ┌─────────────────────┐
│    MLflow       │                   │   Redis Cache        │
│  Experiment     │                   │  (résultats 15min)   │
│  Tracking       │                   │                      │
│  + Model Vers.  │                   │                      │
└─────────────────┘                   └─────────────────────┘
```

---

## 2. Endpoints API — Spécification complète

### Base URL
```
https://api.tsfa.io/v1
```

### Authentification
```
Header: X-RapidAPI-Key: {api_key}
```

---

### 2.1 `POST /forecast/univariate`

Prédiction d'une série temporelle à une seule variable.

**Request Body :**
```json
{
  "series": [120.5, 132.1, 128.7, 145.0, 139.3, 152.8, 148.2],
  "timestamps": ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04",
                  "2024-01-05", "2024-01-06", "2024-01-07"],
  "horizon": 7,
  "frequency": "D",
  "model": "auto",
  "confidence_levels": [0.8, 0.95],
  "seasonality": "auto"
}
```

**Paramètres :**

| Paramètre | Type | Requis | Description |
|---|---|---|---|
| `series` | array[float] | ✅ | Valeurs historiques (min 10, max 50,000) |
| `timestamps` | array[string] | ❌ | ISO 8601. Si absent, fréquence uniforme assumée |
| `horizon` | int | ✅ | Nombre de pas à prédire (max 365) |
| `frequency` | string | ❌ | `"H"` `"D"` `"W"` `"M"` `"Q"` `"Y"` ou `"auto"` |
| `model` | string | ❌ | `"auto"` `"chronos"` `"lstm"` `"arima"` `"ensemble"` |
| `confidence_levels` | array[float] | ❌ | Intervalles de confiance (défaut: [0.8, 0.95]) |
| `seasonality` | string/int | ❌ | `"auto"` ou période (ex: `7` pour hebdomadaire) |

**Response 200 :**
```json
{
  "status": "success",
  "model_used": "chronos-t5-small",
  "forecast": {
    "timestamps": ["2024-01-08", "2024-01-09", "2024-01-10"],
    "mean": [155.2, 158.7, 162.1],
    "lower_80": [148.1, 150.3, 153.2],
    "upper_80": [162.3, 167.1, 171.0],
    "lower_95": [141.2, 143.5, 146.0],
    "upper_95": [169.2, 174.0, 178.2]
  },
  "diagnostics": {
    "trend": "upward",
    "seasonality_detected": true,
    "seasonality_period": 7,
    "series_length": 7,
    "missing_values": 0,
    "stationarity": "non_stationary"
  },
  "meta": {
    "inference_time_ms": 234,
    "request_id": "req_abc123",
    "credits_used": 1
  }
}
```

**Errors :**
```json
{ "status": "error", "code": "SERIES_TOO_SHORT", "message": "Series must have at least 10 observations." }
{ "status": "error", "code": "HORIZON_EXCEEDS_LIMIT", "message": "Horizon cannot exceed 365 for your plan." }
{ "status": "error", "code": "INVALID_FREQUENCY", "message": "Frequency 'X' is not supported." }
```

---

### 2.2 `POST /forecast/multivariate`

Prédiction avec plusieurs variables covariantes.

**Request Body :**
```json
{
  "target": {
    "name": "sales",
    "values": [120.5, 132.1, 128.7, 145.0, 139.3],
    "timestamps": ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"]
  },
  "covariates": [
    {
      "name": "temperature",
      "values": [18.2, 22.1, 19.5, 25.3, 20.1],
      "is_future_known": false
    },
    {
      "name": "is_holiday",
      "values": [0, 0, 1, 0, 0],
      "future_values": [0, 1, 0, 0, 0, 0, 0],
      "is_future_known": true
    }
  ],
  "horizon": 7,
  "frequency": "D",
  "model": "auto"
}
```

**Response 200 :**
```json
{
  "status": "success",
  "model_used": "tide",
  "forecast": {
    "timestamps": ["2024-01-06", "2024-01-07", "2024-01-08"],
    "mean": [142.1, 150.3, 148.7],
    "lower_95": [135.0, 143.2, 141.5],
    "upper_95": [149.2, 157.4, 155.9]
  },
  "feature_importance": {
    "temperature": 0.38,
    "is_holiday": 0.21,
    "lag_1": 0.28,
    "lag_7": 0.13
  },
  "meta": {
    "inference_time_ms": 412,
    "request_id": "req_def456",
    "credits_used": 3
  }
}
```

---

### 2.3 `POST /forecast/batch`

Prédiction sur plusieurs séries simultanément (plans Pro et Ultra).

**Request Body :**
```json
{
  "series_list": [
    { "id": "product_A", "values": [10, 12, 15, 13, 16], "horizon": 7 },
    { "id": "product_B", "values": [100, 95, 102, 98, 107], "horizon": 14 },
    { "id": "product_C", "values": [500, 520, 490, 510, 530], "horizon": 30 }
  ],
  "frequency": "D",
  "model": "auto"
}
```

**Response 200 :**
```json
{
  "status": "success",
  "results": [
    {
      "id": "product_A",
      "forecast": { "mean": [17, 16, 18, 19, 17, 20, 18], "lower_95": [...], "upper_95": [...] }
    },
    {
      "id": "product_B",
      "forecast": { "mean": [105, 108, ...], "lower_95": [...], "upper_95": [...] }
    }
  ],
  "meta": { "total_series": 3, "inference_time_ms": 890, "credits_used": 9 }
}
```

---

### 2.4 `POST /validate`

Valide les performances d'un modèle sur données historiques (backtesting).

**Request Body :**
```json
{
  "series": [120, 132, 128, 145, 139, 152, 148, 160, 155, 168],
  "timestamps": ["2024-01-01", ...],
  "horizon": 3,
  "frequency": "D",
  "model": "auto",
  "n_windows": 3
}
```

**Response 200 :**
```json
{
  "status": "success",
  "backtest_metrics": {
    "mae": 4.23,
    "rmse": 5.81,
    "mape": 3.12,
    "smape": 3.08,
    "coverage_80": 0.82,
    "coverage_95": 0.94
  },
  "windows": [
    { "window": 1, "mae": 4.1, "rmse": 5.5 },
    { "window": 2, "mae": 4.5, "rmse": 6.2 },
    { "window": 3, "mae": 4.1, "rmse": 5.8 }
  ],
  "meta": { "credits_used": 3 }
}
```

---

### 2.5 `GET /models`

Liste les modèles disponibles et leurs caractéristiques.

**Response 200 :**
```json
{
  "models": [
    {
      "id": "chronos",
      "name": "Chronos-T5 (Small)",
      "type": "foundation_model",
      "best_for": ["univariate", "zero-shot", "general purpose"],
      "min_series_length": 10,
      "max_horizon": 365,
      "avg_inference_ms": 250,
      "credits_per_call": 1
    },
    {
      "id": "tide",
      "name": "TiDE",
      "type": "deep_learning",
      "best_for": ["multivariate", "long horizon", "many covariates"],
      "min_series_length": 50,
      "max_horizon": 365,
      "avg_inference_ms": 400,
      "credits_per_call": 3
    },
    {
      "id": "lstm",
      "name": "LSTM Custom (fine-tuned)",
      "type": "deep_learning",
      "best_for": ["noisy series", "non-linear patterns"],
      "min_series_length": 30,
      "max_horizon": 90,
      "avg_inference_ms": 320,
      "credits_per_call": 2
    },
    {
      "id": "arima",
      "name": "AutoARIMA",
      "type": "statistical",
      "best_for": ["short series", "stationary", "interpretability"],
      "min_series_length": 10,
      "max_horizon": 180,
      "avg_inference_ms": 80,
      "credits_per_call": 1
    },
    {
      "id": "ensemble",
      "name": "Ensemble (Chronos + LSTM + ARIMA)",
      "type": "ensemble",
      "best_for": ["highest accuracy", "production use"],
      "min_series_length": 30,
      "max_horizon": 180,
      "avg_inference_ms": 650,
      "credits_per_call": 5
    }
  ]
}
```

---

### 2.6 `GET /usage`

Consommation du plan courant.

**Response 200 :**
```json
{
  "plan": "pro",
  "period": "2026-05",
  "credits_used": 1247,
  "credits_limit": 50000,
  "credits_remaining": 48753,
  "reset_date": "2026-06-01",
  "requests_count": 342
}
```

---

## 3. Règles métier & crédits

### Système de crédits

Chaque appel consomme des crédits selon le modèle utilisé :

| Modèle | Crédits/appel |
|---|---|
| AutoARIMA | 1 |
| Chronos | 1 |
| LSTM | 2 |
| TiDE (multivariate) | 3 |
| Ensemble | 5 |
| Batch : N séries | N × crédits_modèle |
| Validate : N windows | N × crédits_modèle |

### Limites par plan

| Plan | Prix/mois | Crédits/mois | Max horizon | Batch | Multivariate |
|---|---|---|---|---|---|
| **Free** | $0 | 500 | 30 | ❌ | ❌ |
| **Basic** | $49 | 10 000 | 90 | ❌ | ❌ |
| **Pro** | $199 | 50 000 | 365 | ✅ (max 50 séries) | ✅ |
| **Ultra** | $499 | 200 000 | 365 | ✅ (max 500 séries) | ✅ |
| **Enterprise** | Custom | Unlimited | Unlimited | ✅ | ✅ |

### Règles de validation des inputs

```python
VALIDATION_RULES = {
    "min_series_length": 10,
    "max_series_length": 50_000,
    "max_horizon_free": 30,
    "max_horizon_basic": 90,
    "max_horizon_pro_ultra": 365,
    "max_batch_size_pro": 50,
    "max_batch_size_ultra": 500,
    "max_covariates": 20,
    "allowed_frequencies": ["T", "H", "D", "W", "M", "Q", "Y", "auto"],
    "allowed_models": ["auto", "chronos", "lstm", "tide", "arima", "ensemble"]
}
```

---

## 4. Structure du projet

```
tsfa/
├── README.md
├── docker-compose.yml
├── Dockerfile
├── .env.example
├── requirements.txt
│
├── app/                          # FastAPI application
│   ├── main.py                   # Entry point, app config
│   ├── config.py                 # Settings (env vars, constants)
│   ├── dependencies.py           # Auth, rate limit, plan check
│   │
│   ├── routers/
│   │   ├── forecast.py           # /forecast/* endpoints
│   │   ├── validate.py           # /validate endpoint
│   │   ├── models.py             # /models endpoint
│   │   └── usage.py              # /usage endpoint
│   │
│   ├── schemas/
│   │   ├── forecast.py           # Pydantic models request/response
│   │   ├── validate.py
│   │   └── common.py             # Meta, errors, shared models
│   │
│   ├── services/
│   │   ├── forecaster.py         # Orchestration logique métier
│   │   ├── model_selector.py     # Auto-selection du meilleur modèle
│   │   ├── validator.py          # Backtesting logic
│   │   └── credits.py            # Calcul et déduction de crédits
│   │
│   └── middleware/
│       ├── logging.py            # Request logging structuré
│       └── error_handler.py      # Global exception handler
│
├── ml/                           # ML inference layer (déployé sur Modal)
│   ├── modal_app.py              # Modal deployment config
│   ├── models/
│   │   ├── base_model.py         # Interface commune
│   │   ├── chronos_model.py      # Chronos-T5 wrapper
│   │   ├── lstm_model.py         # LSTM custom
│   │   ├── tide_model.py         # TiDE wrapper
│   │   ├── arima_model.py        # AutoARIMA (statsforecast)
│   │   └── ensemble_model.py     # Ensemble combiner
│   │
│   ├── preprocessing/
│   │   ├── cleaner.py            # Missing values, outliers
│   │   ├── feature_engineer.py   # Lags, rolling stats, FFT features
│   │   └── frequency_detector.py # Auto-detect de fréquence
│   │
│   └── postprocessing/
│       ├── confidence.py         # Calcul intervalles de confiance
│       └── diagnostics.py        # Trend, seasonality detection
│
├── benchmarks/                   # Public benchmarks (HuggingFace + docs)
│   ├── run_benchmark.py          # Script de benchmark reproductible
│   ├── datasets/
│   │   ├── m5_sample.csv
│   │   ├── ett_h1_sample.csv
│   │   └── traffic_sample.csv
│   └── results/
│       └── benchmark_results.json
│
├── tests/
│   ├── unit/
│   │   ├── test_schemas.py
│   │   ├── test_model_selector.py
│   │   └── test_preprocessing.py
│   ├── integration/
│   │   ├── test_forecast_endpoint.py
│   │   └── test_validate_endpoint.py
│   └── load/
│       └── locustfile.py         # Load testing
│
├── infra/
│   ├── nginx.conf
│   ├── prometheus.yml
│   └── grafana/
│       └── dashboard.json
│
└── docs/
    ├── quickstart.md
    ├── models.md
    ├── pricing.md
    ├── examples/
    │   ├── python_example.py
    │   ├── javascript_example.js
    │   ├── curl_example.sh
    │   └── notebook_example.ipynb
    └── benchmarks.md
```

---

## 5. Stack technique détaillée

### API Layer
```
FastAPI 0.115+          # Framework API (performances, typing, docs auto)
Pydantic v2             # Validation des schemas request/response
Uvicorn + Gunicorn      # ASGI server (multi-workers)
Redis 7                 # Cache résultats (TTL 15min) + rate limiting
```

### ML Inference
```
Modal.com               # GPU on-demand serverless (A10G ou T4 selon workload)
                        # 0€ si 0 requête — facturation à la milliseconde GPU

Chronos-T5-Small        # Foundation model zero-shot (Amazon Research)
                        # Hugging Face: amazon/chronos-t5-small
TiDE                    # Time-series Dense Encoder (Google Research)
statsforecast           # AutoARIMA rapide (Nixtla — open source)
PyTorch                 # LSTM custom
neuralforecast          # Wrappers Nixtla pour LSTM, TiDE
```

### Infrastructure
```
Hetzner VPS             # CX21 : 2 vCPU, 4GB RAM, 20GB SSD — ~6€/mois
                        # Routing FastAPI uniquement (inférence sur Modal)
Docker + Compose        # Containerisation
GitHub Actions          # CI/CD : tests → build → deploy
Caddy                   # Reverse proxy + HTTPS automatique
```

### Observabilité
```
MLflow                  # Tracking expériences, versioning modèles
Prometheus              # Métriques API (latence, taux d'erreur, credits)
Grafana                 # Dashboard monitoring (Dorian le connaît déjà)
Structlog               # Logging JSON structuré
Sentry                  # Error tracking
```

### Documentation
```
Mintlify                # Docs developer-grade (ou Readme.io)
OpenAPI / Swagger       # Auto-générée par FastAPI
Jupyter Notebooks       # Exemples interactifs → HuggingFace Spaces
```

---

## 6. Auto-selection de modèle (`model: "auto"`)

La logique `model_selector.py` applique les règles suivantes :

```python
def select_model(series_length, horizon, has_covariates, has_seasonality, frequency):

    # Série trop courte pour DL
    if series_length < 30:
        return "arima"

    # Multivarié → TiDE
    if has_covariates:
        return "tide"

    # Longue série, saisonnalité claire, horizon court → Chronos
    if series_length >= 100 and horizon <= 90:
        return "chronos"

    # Horizon long (>90j) et série suffisante → LSTM
    if horizon > 90 and series_length >= 50:
        return "lstm"

    # Défaut → Chronos (meilleur généraliste zero-shot)
    return "chronos"
```

---

## 7. Preprocessing pipeline

Appliqué automatiquement à chaque requête avant l'inférence :

```
Input series
    │
    ▼
1. VALIDATION
   - Type check (numeric, no infinite values)
   - Length check (min 10 observations)
   - Timestamps consistency (gaps détectés et reportés)
    │
    ▼
2. MISSING VALUES
   - Détection automatique
   - Strategy : interpolation linéaire si <5% missing
   - Strategy : forward-fill si série régulière
   - Warning retourné si >10% missing
    │
    ▼
3. OUTLIER DETECTION (non-destructif)
   - IQR method
   - Les outliers sont reportés dans diagnostics, pas supprimés
    │
    ▼
4. FREQUENCY DETECTION (si "auto")
   - Analyse des timestamps pour inférer H/D/W/M
    │
    ▼
5. SEASONALITY DETECTION
   - FFT + ACF pour détecter période dominante
    │
    ▼
6. MODEL DISPATCH → inference
```

---

## 8. Roadmap de développement

### Phase 1 — MVP (Semaines 1-4)

**Semaine 1 : Fondations**
- [ ] Setup repo GitHub + structure projet
- [ ] Docker + docker-compose (FastAPI + Redis)
- [ ] Hetzner VPS + Caddy + HTTPS
- [ ] Endpoint `/forecast/univariate` avec AutoARIMA (statistique, rapide, 0 GPU)
- [ ] Pydantic schemas complets
- [ ] Tests unitaires de base

**Semaine 2 : Modèles ML**
- [ ] Setup Modal.com (compte + premier déploiement)
- [ ] Intégration Chronos-T5-Small sur Modal
- [ ] Intégration LSTM via neuralforecast sur Modal
- [ ] Preprocessing pipeline complet
- [ ] Auto-selection de modèle

**Semaine 3 : Endpoints complets + polish**
- [ ] Endpoint `/forecast/multivariate` (TiDE)
- [ ] Endpoint `/validate` (backtesting)
- [ ] Endpoint `/models` et `/usage`
- [ ] Global error handler + logging structuré
- [ ] Cache Redis (éviter re-inférence sur requêtes identiques)

**Semaine 4 : Benchmark + Publication**
- [ ] Script de benchmark sur M5, ETT, Traffic datasets
- [ ] Résultats JSON publics + markdown `benchmarks.md`
- [ ] Documentation complète (Mintlify)
- [ ] Exemples Python / JS / curl
- [ ] Publication RapidAPI (profil, description, plans tarifaires)
- [ ] Publication modèle HuggingFace Hub (visibilité communauté)

### Phase 2 — Scale (Mois 2-3)

- [ ] Endpoint `/forecast/batch` (plans Pro/Ultra)
- [ ] Intégration Stripe pour billing custom (hors RapidAPI)
- [ ] Dashboard usage client (HTML statique ou React simple)
- [ ] Load testing (Locust) + optimisation latence
- [ ] Dossier AWS Marketplace SaaS

### Phase 3 — Expansion (Mois 4-6)

- [ ] Fine-tuning Chronos sur données domaine (energy, logistics)
- [ ] SDK Python officiel (`pip install tsfa-client`)
- [ ] Lancement Niche 2 (Document Intelligence) ou Niche 3 (Anomaly Detection)
- [ ] Webhooks pour jobs asynchrones longs (batch volumineux)

---

## 9. Fichiers de configuration essentiels

### `.env.example`
```env
# API
API_HOST=0.0.0.0
API_PORT=8000
API_VERSION=v1
DEBUG=false

# Redis
REDIS_URL=redis://localhost:6379/0
CACHE_TTL_SECONDS=900

# Modal (ML inference)
MODAL_TOKEN_ID=your_modal_token_id
MODAL_TOKEN_SECRET=your_modal_token_secret
MODAL_APP_NAME=tsfa-inference

# RapidAPI (webhook validation)
RAPIDAPI_PROXY_SECRET=your_rapidapi_proxy_secret

# MLflow
MLFLOW_TRACKING_URI=http://localhost:5000

# Sentry
SENTRY_DSN=your_sentry_dsn

# Plans (crédits/mois)
PLAN_FREE_CREDITS=500
PLAN_BASIC_CREDITS=10000
PLAN_PRO_CREDITS=50000
PLAN_ULTRA_CREDITS=200000
```

### `docker-compose.yml`
```yaml
version: '3.9'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      - redis
    volumes:
      - ./app:/app/app
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    restart: unless-stopped

  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./infra/prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    volumes:
      - ./infra/grafana:/etc/grafana/provisioning
```

### `requirements.txt`
```
# API
fastapi==0.115.0
uvicorn[standard]==0.32.0
pydantic==2.9.0
python-multipart==0.0.12
structlog==24.4.0
sentry-sdk[fastapi]==2.17.0

# Cache
redis==5.1.1

# ML - Statistical
statsforecast==1.7.5       # AutoARIMA rapide

# ML - Neural (via Modal, mais listé ici pour la cohérence)
neuralforecast==1.7.5      # TiDE, LSTM, NHITS
torch==2.4.0
transformers==4.46.0       # Chronos
chronos-forecasting==1.4.0 # Amazon Chronos

# Preprocessing
pandas==2.2.3
numpy==1.26.4
scipy==1.14.1
statsmodels==0.14.4

# MLOps
mlflow==2.17.0

# Tests
pytest==8.3.3
httpx==0.27.2              # Test client FastAPI
locust==2.32.0             # Load testing
```

---

## 10. Exemple de code — Intégration client (docs publiques)

### Python
```python
import requests

API_KEY = "your_rapidapi_key"
BASE_URL = "https://tsfa-api.p.rapidapi.com/v1"

headers = {
    "X-RapidAPI-Key": API_KEY,
    "Content-Type": "application/json"
}

response = requests.post(
    f"{BASE_URL}/forecast/univariate",
    json={
        "series": [120, 132, 128, 145, 139, 152, 148, 160, 155, 168],
        "horizon": 7,
        "frequency": "D",
        "model": "auto"
    },
    headers=headers
)

data = response.json()
print(data["forecast"]["mean"])  # [172.3, 175.1, ...]
```

### JavaScript (Node)
```javascript
const response = await fetch("https://tsfa-api.p.rapidapi.com/v1/forecast/univariate", {
  method: "POST",
  headers: {
    "X-RapidAPI-Key": "your_rapidapi_key",
    "Content-Type": "application/json"
  },
  body: JSON.stringify({
    series: [120, 132, 128, 145, 139, 152, 148, 160, 155, 168],
    horizon: 7,
    frequency: "D",
    model: "auto"
  })
});

const data = await response.json();
console.log(data.forecast.mean);
```

### cURL
```bash
curl -X POST "https://tsfa-api.p.rapidapi.com/v1/forecast/univariate" \
  -H "X-RapidAPI-Key: your_rapidapi_key" \
  -H "Content-Type: application/json" \
  -d '{
    "series": [120, 132, 128, 145, 139, 152, 148, 160, 155, 168],
    "horizon": 7,
    "frequency": "D",
    "model": "auto"
  }'
```

---

## 11. Checklist avant publication RapidAPI

- [ ] Endpoint `/forecast/univariate` fonctionnel et testé
- [ ] Latence P95 < 2 secondes pour univarié Chronos
- [ ] Documentation complète sur Mintlify (au moins quickstart + référence API)
- [ ] Benchmark public sur 3 datasets (M5 / ETT / Traffic) → fichier `benchmarks.md`
- [ ] Page RapidAPI complète : description, logo, use cases, plans tarifaires
- [ ] Free tier testé manuellement (rate limit vérifié)
- [ ] Error messages compréhensibles et documentés
- [ ] Monitoring actif (Grafana + alertes Sentry)
- [ ] Modèle publié sur HuggingFace Hub (même si petit) + lien vers l'API dans le README

---

## 12. KPIs à suivre dès le lancement

| KPI | Cible Mois 1 | Cible Mois 3 | Cible Mois 6 |
|---|---|---|---|
| Subscriptions Free | 50 | 200 | 500 |
| Conversion Free→Payant | - | 5% | 8% |
| Clients payants | 0 | 10 | 40 |
| MRR | $0 | $1,500 | $8,000 |
| P95 Latence univarié | <3s | <2s | <1.5s |
| Uptime | 99% | 99.5% | 99.9% |
| RapidAPI rating | - | ≥4.5/5 | ≥4.7/5 |
