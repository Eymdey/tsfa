# TSFA — Prompt Semaine 2 : Modal.com + Chronos + Auto-selection réelle

## CONTEXTE

La Semaine 1 est terminée et validée :
- 56/56 tests passent
- `POST /v1/forecast/univariate` fonctionne avec AutoARIMA en local
- Docker + Redis opérationnels
- Toute la structure du projet est en place

Tu attaques maintenant la **Semaine 2 du roadmap** défini dans `project-specs.md`.

Relis `project-specs.md` sections 5, 6, 7 et 8 avant de commencer.

---

## OBJECTIF DE LA SEMAINE 2

Remplacer le modèle AutoARIMA seul par une **couche d'inférence multi-modèles réelle**,
avec dispatch vers Modal.com pour les modèles GPU (Chronos, LSTM), et auto-selection
intelligente selon les caractéristiques de la série.

---

## CE QUE TU DOIS CONSTRUIRE

### 1. Setup Modal.com

Installe et configure le SDK Modal :

```bash
pip install modal
modal setup  # authentification interactive
```

Crée `ml/modal_app.py` : l'application Modal principale.

```python
# Structure attendue de modal_app.py
import modal

app = modal.App("tsfa-inference")

# Image avec toutes les dépendances ML lourdes
inference_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install([
        "chronos-forecasting==1.4.0",
        "neuralforecast==1.7.5",
        "statsforecast==1.7.5",
        "torch==2.4.0",
        "transformers==4.46.0",
        "pandas==2.2.3",
        "numpy==1.26.4",
    ])
)
```

Le fichier doit contenir les **3 fonctions Modal déployables** :
- `run_chronos(payload: dict) -> dict`
- `run_lstm(payload: dict) -> dict`
- `run_arima(payload: dict) -> dict` (migration de la version locale)

Chaque fonction reçoit un dict sérialisable JSON et retourne un dict.
Aucun objet pandas/numpy dans les arguments — sérialise en listes Python avant dispatch.

---

### 2. Chronos-T5-Small — wrapper complet

Crée `ml/models/chronos_model.py` :

```python
# Interface attendue
class ChronosModel:
    model_id = "amazon/chronos-t5-small"

    def predict(
        self,
        series: list[float],
        horizon: int,
        confidence_levels: list[float] = [0.8, 0.95],
        num_samples: int = 20,        # samples pour intervalles de confiance
    ) -> dict:
        """
        Retourne :
        {
            "mean": [...],
            "quantiles": {
                "0.1": [...], "0.2": [...],
                "0.8": [...], "0.9": [...],
                "0.025": [...], "0.975": [...]
            },
            "model_name": "chronos-t5-small"
        }
        """
```

Points d'attention :
- Charge le modèle **une seule fois** avec `@modal.enter()` (pas à chaque requête)
- `num_samples=20` par défaut pour les intervalles de confiance
- Les intervalles de confiance sont calculés depuis les quantiles des samples
- Gère le cas où `len(series) < 12` → fallback silencieux vers ARIMA

---

### 3. LSTM custom — wrapper complet

Crée `ml/models/lstm_model.py` via `neuralforecast` :

```python
from neuralforecast import NeuralForecast
from neuralforecast.models import LSTM

class LSTMModel:
    def predict(
        self,
        series: list[float],
        horizon: int,
        frequency: str,
        confidence_levels: list[float] = [0.8, 0.95],
    ) -> dict:
        """
        Utilise neuralforecast LSTM avec LEVEL pour les intervalles.
        Entraînement à la volée sur la série fournie (pas de pré-entraînement).
        max_steps=50 pour garder la latence < 5s.
        """
```

Points d'attention :
- `max_steps=50` — compromis vitesse/qualité acceptable pour une API
- Format neuralforecast : DataFrame avec colonnes `unique_id`, `ds`, `y`
- `LEVEL=[80, 95]` pour les intervalles de confiance
- Gère les séries courtes (< 30 obs) → fallback vers Chronos

---

### 4. Migration AutoARIMA vers Modal

Migre le modèle ARIMA existant dans `ml/models/arima_model.py` pour qu'il
soit aussi exécutable via Modal (cohérence), tout en gardant un mode
`local=True` pour les tests sans connexion Modal.

```python
class ARIMAModel:
    def predict(self, series, horizon, frequency, confidence_levels, local=False):
        if local:
            return self._predict_local(...)
        else:
            return self._predict_modal(...)
```

---

### 5. Auto-selection de modèle — logique réelle

Mets à jour `app/services/model_selector.py` avec la logique **complète** des
specs (section 6), plus ces règles supplémentaires :

```python
def select_model(
    series_length: int,
    horizon: int,
    has_covariates: bool,
    frequency: str,
    requested_model: str,  # "auto" ou modèle spécifique
) -> tuple[str, str]:
    """
    Retourne (model_id, reason) où reason explique le choix.

    Règles de priorité :
    1. Si requested_model != "auto" → retourne le modèle demandé directement
    2. Si series_length < 12 → "arima" (Chronos ne supporte pas < 12 obs)
    3. Si series_length < 30 → "arima" (LSTM ne supporte pas < 30 obs)
    4. Si has_covariates → "tide" (stub Phase 1, retourne 501)
    5. Si series_length >= 100 et horizon <= 90 → "chronos"
    6. Si horizon > 90 et series_length >= 50 → "lstm"
    7. Défaut → "chronos"
    """
```

---

### 6. Dispatcher central — mise à jour du forecaster

Mets à jour `app/services/forecaster.py` pour dispatcher vers le bon modèle :

```python
class ForecastingService:
    async def forecast_univariate(self, request: UnivariateForecastRequest) -> ForecastResponse:
        # 1. Preprocessing (existant)
        # 2. select_model() → model_id
        # 3. Dispatch :
        #    - "arima"   → ARIMAModel (local ou Modal selon config)
        #    - "chronos" → appel Modal run_chronos.remote(payload)
        #    - "lstm"    → appel Modal run_lstm.remote(payload)
        #    - "tide"    → HTTPException 501 (Phase 3)
        #    - "ensemble"→ HTTPException 501 (Phase 3)
        # 4. Post-processing + diagnostics (existant)
        # 5. Cache Redis (existant)
        # 6. Retourne ForecastResponse
```

Variable d'environnement `USE_MODAL=true/false` dans `.env` :
- `false` → tout tourne en local (ARIMA uniquement) — mode dev/test
- `true`  → dispatch Chronos et LSTM vers Modal — mode production

---

### 7. Mise à jour `GET /v1/models`

Le endpoint `/v1/models` doit maintenant retourner les vrais états :

```json
{
  "models": [
    { "id": "arima",   "available": true,  "backend": "local" },
    { "id": "chronos", "available": true,  "backend": "modal" },
    { "id": "lstm",    "available": true,  "backend": "modal" },
    { "id": "tide",    "available": false, "backend": "modal", "coming": "phase_3" },
    { "id": "ensemble","available": false, "backend": "modal", "coming": "phase_3" }
  ]
}
```

---

### 8. Gestion des erreurs Modal

Ajoute dans `app/middleware/error_handler.py` :

- `ModalTimeoutError` → HTTP 503 + message `"ML inference timeout. Please retry."`
- `ModalConnectionError` → HTTP 503 + fallback automatique vers ARIMA avec
  warning dans la réponse : `"meta.fallback_used": true, "meta.fallback_reason": "modal_unavailable"`
- Log toutes les erreurs Modal avec structlog niveau ERROR

---

### 9. Tests — mise à jour complète

**Tests unitaires à ajouter :**
- `tests/unit/test_model_selector.py` : au moins 8 cas couvrant toutes les
  branches de la logique de sélection
- `tests/unit/test_chronos_model.py` : tests avec mock Modal (ne pas appeler
  Modal réellement en CI) — utilise `unittest.mock.patch`
- `tests/unit/test_lstm_model.py` : idem avec mock

**Tests d'intégration à mettre à jour :**
- `tests/integration/test_forecast_endpoint.py` : ajoute des cas avec
  `model="chronos"` et `model="lstm"` en mode `USE_MODAL=false`
  (doivent retourner une réponse ARIMA de fallback ou 503 selon config)

**Ne pas casser les 56 tests existants.**
Cible finale : **70+ tests, tous verts**.

---

### 10. Benchmark public — script final

Crée `benchmarks/run_benchmark.py` :

```python
"""
Benchmark TSFA vs baseline sur 3 datasets publics :
- M5 Competition (retail demand forecasting)
- ETT-h1 (electricity transformer temperature)  
- Exchange Rate (Autoformer paper)

Métriques : MAE, RMSE, MAPE, sMAPE
Modèles testés : arima, chronos (si Modal dispo), moyenne naïve (baseline)

Usage :
    python benchmarks/run_benchmark.py --model all --output benchmarks/results/
    python benchmarks/run_benchmark.py --model chronos --local-only
"""
```

Le script génère `benchmarks/results/benchmark_results.json` et un
`benchmarks/results/README.md` formaté pour être publié directement
sur HuggingFace Hub (tableau markdown des résultats).

---

## CONTRAINTES STRICTES

- ❌ Ne pas implémenter TiDE ni Ensemble (Phase 3)
- ❌ Ne pas implémenter `/forecast/multivariate` (Phase 3)
- ❌ Ne pas implémenter `/forecast/batch` (Phase 3)
- ✅ `USE_MODAL=false` doit permettre de faire tourner tous les tests sans
  connexion internet ni compte Modal
- ✅ Le fallback ARIMA doit être transparent pour le client (warn dans meta,
  pas d'erreur 5xx sauf timeout)
- ✅ Toujours pinner les versions dans requirements.txt

---

## ORDRE D'EXÉCUTION

1. `pip install modal && modal setup` → vérifie que le compte est actif
2. Crée `ml/modal_app.py` + déploie avec `modal deploy ml/modal_app.py`
3. Implémente et teste `ChronosModel` en isolation (script de test rapide)
4. Implémente et teste `LSTMModel` en isolation
5. Mets à jour `model_selector.py` + lance ses tests unitaires
6. Mets à jour `forecaster.py` avec le dispatcher
7. Lance `docker-compose up` + teste les 3 modèles via curl
8. Ajoute les nouveaux tests + vérifie que les 56 anciens passent toujours
9. Lance le benchmark sur ETT-h1 (le plus léger des 3 datasets)

---

## COMMANDES DE VALIDATION FINALE

Ces 3 curls doivent tous retourner `"status": "success"` avec des valeurs
numériques cohérentes dans `forecast.mean` :

```bash
# AutoARIMA (local, rapide)
curl -X POST http://localhost:8000/v1/forecast/univariate \
  -H "Content-Type: application/json" -H "X-Plan: free" \
  -d '{"series":[120,132,128,145,139,152,148,160,155,168,163,175],"horizon":7,"model":"arima"}'

# Chronos (via Modal)
curl -X POST http://localhost:8000/v1/forecast/univariate \
  -H "Content-Type: application/json" -H "X-Plan: pro" \
  -d '{"series":[120,132,128,145,139,152,148,160,155,168,163,175,170,182,178,190,185,195],"horizon":14,"model":"chronos"}'

# Auto-selection → doit choisir Chronos (série >= 30, horizon <= 90)
curl -X POST http://localhost:8000/v1/forecast/univariate \
  -H "Content-Type: application/json" -H "X-Plan: pro" \
  -d '{"series":[120,132,128,145,139,152,148,160,155,168,163,175,170,182,178,190,185,195,200,195,210,205,215,220,218,225,230,222,235,240],"horizon":30,"model":"auto"}'
```

**Cible : 70+ tests verts + les 3 curls en succès = Semaine 2 terminée.**
