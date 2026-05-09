# TSFA — Prompt Semaine 3 : /validate + /batch + Publication RapidAPI

## ÉTAPE PRÉLIMINAIRE OBLIGATOIRE — À faire avant tout le reste

**Avant d'écrire une seule ligne de code, tu dois activer Chronos en production
et vérifier qu'il fonctionne réellement via Modal.**

### 1. Active USE_MODAL=true dans .env

Lis le fichier `.env` actuel, trouve la ligne `USE_MODAL=false` et remplace-la
par `USE_MODAL=true`. Utilise sed ou édite directement le fichier :

```bash
sed -i 's/USE_MODAL=false/USE_MODAL=true/' .env
```

Vérifie que la modification est bien appliquée :

```bash
grep USE_MODAL .env
# Doit afficher : USE_MODAL=true
```

### 2. Redémarre l'API pour charger la nouvelle config

```bash
docker-compose restart api
```

Attends 5 secondes puis vérifie que l'API répond toujours :

```bash
curl http://localhost:8000/health
# Doit retourner {"status":"ok",...}
```

### 3. Valide que Chronos est maintenant réel (pas ARIMA fallback)

Lance ce curl et vérifie que `model_used` affiche `chronos-t5-small`
et NON `arima`. Si `model_used` est encore `arima`, il y a un problème
de config ou de connexion Modal à diagnostiquer avant de continuer.

```bash
curl -X POST http://localhost:8000/v1/forecast/univariate \
  -H "Content-Type: application/json" -H "X-Plan: pro" \
  -d '{
    "series": [120,132,128,145,139,152,148,160,155,168,163,175,170,182,178,190,185,195],
    "horizon": 14,
    "model": "chronos"
  }'
```

**Résultat attendu :** `"model_used": "chronos-t5-small"` dans la réponse JSON.

**Si le résultat est encore `"model_used": "arima"` :**
- Vérifie que Modal est bien authentifié : `modal token list`
- Vérifie que le deploy est actif : `modal app list`
- Relis les logs Docker : `docker-compose logs api --tail=50`
- Relance le deploy si nécessaire : `modal deploy ml/modal_app.py`
- Corrige le problème avant de passer à la suite — ne pas continuer avec
  USE_MODAL=true si Chronos ne répond pas réellement

### 4. Seulement quand Chronos est confirmé → passe à la suite

---

## CONTEXTE

Semaines 1 et 2 validées :
- 90/90 tests passent
- POST /v1/forecast/univariate fonctionnel (ARIMA local + Chronos/LSTM via Modal)
- USE_MODAL=true maintenant activé → Chronos réel sur GPU Modal (confirmé à l'étape préliminaire)
- Benchmarks publics générés (ETT-h1, M5, Exchange Rate)
- Docker + Redis + Caddy opérationnels sur VPS Hetzner

Semaine 3 = dernière semaine avant publication RapidAPI.
Objectif : compléter les endpoints manquants, polish prod, et publier.

Relis project-specs.md sections 2.3, 2.4, et 8 (Phase 2 roadmap) avant de commencer.

---

## CE QUE TU DOIS CONSTRUIRE

### 1. POST /v1/validate — backtesting réel

Implémente l'endpoint complet défini dans project-specs.md section 2.4.

Service `app/services/validator.py` :

```python
class BacktestingService:
    def run_backtest(
        self,
        series: list[float],
        timestamps: list[str] | None,
        horizon: int,
        frequency: str,
        model: str,
        n_windows: int,          # nombre de fenêtres de test (défaut: 3)
    ) -> ValidateResponse:
        """
        Sliding window cross-validation :

        Pour chaque fenêtre i de 1 à n_windows :
          - train = series[:-(horizon * (n_windows - i + 1))]
          - test  = series[len(train):len(train) + horizon]
          - prédit avec le modèle sélectionné
          - calcule MAE, RMSE, MAPE sur cette fenêtre

        Agrège les métriques sur toutes les fenêtres (moyenne).
        Calcule aussi coverage_80 et coverage_95 :
          → % de vraies valeurs dans l'intervalle de confiance prédit.

        Contrainte : series doit avoir min (horizon * n_windows * 2) observations.
        Sinon → HTTP 422 avec message explicite.
        """
```

Métriques à calculer dans `ml/postprocessing/metrics.py` (nouveau fichier) :

```python
def mae(y_true, y_pred) -> float
def rmse(y_true, y_pred) -> float
def mape(y_true, y_pred) -> float   # gère division par zéro
def smape(y_true, y_pred) -> float
def coverage(y_true, lower, upper) -> float  # % dans l'intervalle
```

Réponse conforme au schema section 2.4 des specs : `backtest_metrics` global
+ détail par `windows` + `meta.credits_used`.

Crédits consommés : `n_windows × credits_du_modèle`.

---

### 2. POST /v1/forecast/batch — traitement multi-séries

Implémente l'endpoint complet défini dans project-specs.md section 2.3.

Règles :
- Plan free/basic → HTTP 403 `"Batch forecasting requires Pro plan or above"`
- Plan pro → max 50 séries par requête
- Plan ultra → max 500 séries par requête
- Traitement en parallèle avec `asyncio.gather()` — pas séquentiel
- Si une série échoue → inclure `"error": "message"` dans son résultat,
  ne pas faire échouer tout le batch
- `meta.credits_used` = somme des crédits de toutes les séries

```python
# Structure de réponse pour une série en erreur dans le batch
{
  "id": "product_X",
  "error": "Series too short: minimum 10 observations required",
  "forecast": null
}
```

---

### 3. POST /v1/validate — stub → réel (même chose pour batch)

Retire les réponses 501 existantes et remplace par les vraies implémentations.
Mets à jour les routes dans `app/routers/forecast.py` et `app/routers/validate.py`.

---

### 4. Système de crédits — implémentation réelle

Jusqu'ici `GET /v1/usage` retourne des données mockées.
Implémente le tracking réel dans Redis :

```python
# app/services/credits.py

class CreditsService:
    def __init__(self, redis_client):
        self.redis = redis_client

    def get_key(self, api_key: str, period: str) -> str:
        return f"credits:{api_key}:{period}"  # period = "2026-05"

    async def consume(self, api_key: str, amount: int) -> dict:
        """
        Déduit `amount` crédits. Retourne :
        { "credits_used": int, "credits_remaining": int, "limit_reached": bool }
        Lève HTTP 429 si credits_remaining <= 0.
        """

    async def get_usage(self, api_key: str) -> UsageResponse:
        """Lit les crédits depuis Redis pour la période courante."""
```

Limites par plan (depuis config.py) :
- free  : 500 crédits/mois
- basic : 10 000
- pro   : 50 000
- ultra : 200 000

En Phase 1, l'api_key = valeur du header `X-RapidAPI-User` (string quelconque).
Pour les tests locaux : header `X-Plan` simulé comme en S1/S2.

`GET /v1/usage` doit maintenant retourner les vraies valeurs Redis.

---

### 5. Rate limiting par plan

Dans `app/dependencies.py`, ajoute un rate limiter basé sur Redis :

```python
# Limites de requêtes par minute selon le plan
RATE_LIMITS = {
    "free":   10,   # req/min
    "basic":  30,
    "pro":    100,
    "ultra":  300,
}
```

HTTP 429 avec header `Retry-After: 60` si dépassé.

---

### 6. Polish production obligatoire

Ces éléments sont requis avant publication RapidAPI :

**a) Health check enrichi**
```json
GET /health
{
  "status": "ok",
  "version": "1.0.0",
  "modal_connected": true,
  "redis_connected": true,
  "uptime_seconds": 3842
}
```

**b) Headers de réponse**
Ajoute sur toutes les réponses :
```
X-Request-Id: req_abc123
X-Credits-Used: 1
X-Credits-Remaining: 49999
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 99
```

**c) Compression gzip**
```python
from fastapi.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
```

**d) Timeout global**
Toute requête d'inférence > 30 secondes → HTTP 503 automatique.

**e) CORS propre**
```python
origins = ["*"]  # RapidAPI forward depuis n'importe quel domaine client
```

---

### 7. Documentation finale pour RapidAPI

Crée ou mets à jour ces fichiers pour qu'ils soient prêts à copier-coller
dans l'interface RapidAPI lors de la publication :

**`docs/rapidapi/description.md`** :
```markdown
# TSFA — Time Series Forecasting API

Professional-grade time series forecasting API powered by foundation models
(Chronos-T5) and deep learning (LSTM), with AutoARIMA fallback.

## What you can do
- Forecast any univariate time series (sales, energy, traffic, finance...)
- Multivariate forecasting with covariates [Pro]
- Batch forecasting for 50-500 series simultaneously [Pro/Ultra]
- Backtesting with sliding window cross-validation

## Why TSFA
- Zero setup : send your data, get forecasts in <2s
- Calibrated confidence intervals (80% and 95%)
- Auto model selection : we pick the best model for your data
- Benchmarked on M5, ETT-h1, Exchange Rate datasets (see /benchmark tab)

## Models available
| Model | Type | Best for |
|---|---|---|
| AutoARIMA | Statistical | Short series, interpretability |
| Chronos-T5 | Foundation model | General purpose, zero-shot |
| LSTM | Deep Learning | Long horizon, complex patterns |

## Quick start (Python)
[voir docs/examples/python_example.py]

## Benchmarks
[voir benchmarks/results/README.md]
```

**`docs/rapidapi/pricing.md`** :
```markdown
| Plan | Price | Credits/month | Batch | Max Horizon |
|---|---|---|---|---|
| Free | $0 | 500 | No | 30 days |
| Basic | $49/mo | 10,000 | No | 90 days |
| Pro | $199/mo | 50,000 | Yes (50 series) | 365 days |
| Ultra | $499/mo | 200,000 | Yes (500 series) | 365 days |

1 credit = 1 AutoARIMA or Chronos call
2 credits = 1 LSTM call
5 credits = 1 Ensemble call
```

---

### 8. Tests — mise à jour complète

**Nouveaux tests à écrire :**

`tests/unit/test_metrics.py` :
- MAE, RMSE, MAPE, sMAPE sur valeurs connues
- Coverage sur intervalles connus
- Cas division par zéro dans MAPE

`tests/unit/test_credits.py` :
- Consume crédits, vérifier décompte Redis
- Dépassement de limite → 429
- Reset mensuel

`tests/integration/test_validate_endpoint.py` :
- Cas succès (série suffisamment longue)
- Série trop courte → 422
- n_windows=1, 3, 5

`tests/integration/test_batch_endpoint.py` :
- Plan free → 403
- Batch de 3 séries plan pro → succès
- Batch avec une série invalide → résultat partiel, pas de 5xx
- Dépassement max_batch_size → 422

`tests/integration/test_rate_limiting.py` :
- 11 requêtes plan free en 1 minute → la 11ème retourne 429

**Ne pas casser les 90 tests existants.**
Cible : **120+ tests, tous verts.**

---

## CONTRAINTES STRICTES

- ❌ Ne pas implémenter TiDE ni Ensemble
- ❌ Ne pas implémenter /forecast/multivariate (stub 501 reste en place)
- ✅ USE_MODAL=true en production, USE_MODAL=false en tests
- ✅ Tous les nouveaux endpoints conformes aux schemas des specs
- ✅ Aucune régression sur les 90 tests existants

---

## ORDRE D'EXÉCUTION

1. Crée `ml/postprocessing/metrics.py` + tests unitaires → tous verts
2. Implémente `BacktestingService` + endpoint `/validate` → test manuel curl
3. Implémente endpoint `/forecast/batch` → test manuel curl
4. Implémente `CreditsService` Redis → mets à jour `/usage`
5. Ajoute rate limiting dans `dependencies.py`
6. Applique le polish production (headers, gzip, health check enrichi)
7. Génère les fichiers de documentation RapidAPI
8. Lance la suite complète de tests → 120+ verts
9. Redémarre docker-compose et valide les 5 curls ci-dessous

---

## COMMANDES DE VALIDATION FINALE

```bash
# 1. Validate endpoint
curl -X POST http://localhost:8000/v1/validate \
  -H "Content-Type: application/json" -H "X-Plan: pro" \
  -d '{
    "series": [120,132,128,145,139,152,148,160,155,168,163,175,170,182,178,190,185,195,200,195,210,205,215,220,218,225,230,222,235,240],
    "horizon": 5,
    "frequency": "D",
    "model": "arima",
    "n_windows": 3
  }'
# Attendu : backtest_metrics avec MAE, RMSE, MAPE, coverage_80, coverage_95

# 2. Batch endpoint
curl -X POST http://localhost:8000/v1/forecast/batch \
  -H "Content-Type: application/json" -H "X-Plan: pro" \
  -d '{
    "series_list": [
      {"id": "series_A", "values": [120,132,128,145,139,152,148,160,155,168,163,175], "horizon": 7},
      {"id": "series_B", "values": [500,520,490,510,530,515,540,525,550,535,560,545], "horizon": 14}
    ],
    "frequency": "D",
    "model": "arima"
  }'
# Attendu : results array avec 2 éléments, chacun avec forecast.mean

# 3. Batch refusé sur plan free
curl -X POST http://localhost:8000/v1/forecast/batch \
  -H "Content-Type: application/json" -H "X-Plan: free" \
  -d '{"series_list": [{"id": "A", "values": [1,2,3,4,5,6,7,8,9,10], "horizon": 3}], "frequency": "D"}'
# Attendu : HTTP 403

# 4. Usage avec vrais crédits
curl http://localhost:8000/v1/usage -H "X-Plan: pro" -H "X-RapidAPI-User: test-user-123"
# Attendu : credits_used > 0 (après les curls précédents)

# 5. Health check enrichi
curl http://localhost:8000/health
# Attendu : modal_connected, redis_connected, uptime_seconds
```

**Cible : 120+ tests verts + 5 curls en succès = Semaine 3 terminée = prêt pour publication RapidAPI.**
