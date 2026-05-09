# TSFA — Prompt Semaine 4 : Publication RapidAPI + HuggingFace Hub + Production

## CONTEXTE

Semaines 1, 2, 3 validées :
- 154/154 tests passent
- Tous les endpoints fonctionnels : /forecast/univariate, /validate, /forecast/batch
- USE_MODAL=true → Chronos-T5 réel sur GPU Modal
- Fallback ARIMA transparent (modal_unavailable → fallback_used=true, pas de 5xx)
- Système de crédits Redis opérationnel
- Rate limiting par plan actif
- Benchmarks publics générés (ETT-h1, M5, Exchange Rate)
- Documentation RapidAPI dans docs/rapidapi/

Semaine 4 = mise en production réelle et publication sur les marketplaces.
Pas de nouvelles fonctionnalités — seulement du polish, de la sécurité, et la publication.

---

## ÉTAPE PRÉLIMINAIRE — Vérification état prod

Avant tout, vérifie que tout tourne correctement :

```bash
docker-compose ps
# Tous les services doivent être "Up"

curl http://localhost:8000/health
# modal_connected: true, redis_connected: true

pytest --tb=short
# 154 passed, 0 failed

curl -X POST http://localhost:8000/v1/forecast/univariate \
  -H "Content-Type: application/json" -H "X-Plan: pro" \
  -d '{"series":[120,132,128,145,139,152,148,160,155,168,163,175,170,182],"horizon":7,"model":"chronos"}'
# model_used: chronos-t5-small
```

Si un check échoue → diagnostique et corrige avant de continuer.

---

## CE QUE TU DOIS FAIRE

### 1. Sécurisation production — obligatoire avant exposition publique

**a) Variables d'environnement — audit complet**

Lis `.env` et `.env.example`. Vérifie qu'aucune valeur sensible n'est
hardcodée dans le code Python. Génère un vrai `SECRET_KEY` :

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Mets à jour `.env` avec cette valeur pour `SECRET_KEY`.

**b) RapidAPI Proxy Secret — validation obligatoire**

RapidAPI forward toutes les requêtes avec le header `X-RapidAPI-Proxy-Secret`.
Sans cette validation, n'importe qui peut appeler ton API directement
en bypassant RapidAPI (et donc le billing).

Dans `app/dependencies.py`, ajoute une dépendance `verify_rapidapi_proxy` :

```python
async def verify_rapidapi_proxy(
    request: Request,
    x_rapidapi_proxy_secret: str | None = Header(default=None)
):
    """
    En production (ENVIRONMENT=production) :
      - Vérifie que X-RapidAPI-Proxy-Secret == RAPIDAPI_PROXY_SECRET depuis .env
      - Si absent ou incorrect → HTTP 403
    En développement (ENVIRONMENT=development) :
      - Skip la vérification (pour les tests locaux)
    """
```

Applique cette dépendance sur **tous les endpoints** sauf /health et /v1/models.

Ajoute `ENVIRONMENT=production` dans `.env` pour le VPS.
Ajoute `ENVIRONMENT=development` dans la config de test.

**c) Limitation de la taille des payloads**

Dans `app/main.py`, ajoute :
```python
# Max payload : 10MB (évite les attaques par série géante)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # RapidAPI forward depuis plusieurs IPs
)
```

Dans les schemas Pydantic, ajoute des contraintes max sur les arrays :
- `series` : max 50 000 valeurs
- `series_list` (batch) : max 500 séries, chaque série max 50 000 valeurs
- `covariates` : max 20 covariables

**d) Logs — supprime les données sensibles**

Dans `app/middleware/logging.py`, assure-toi que les logs ne contiennent
jamais les valeurs brutes des séries (elles peuvent être confidentielles
pour les clients). Log uniquement : longueur, endpoint, plan, durée, status.

```python
# PAS ça :
logger.info("request", payload=request_body)

# OUI ça :
logger.info("forecast_request",
    series_length=len(request.series),
    horizon=request.horizon,
    model=request.model,
    plan=plan,
)
```

---

### 2. Caddy — configuration domaine public

L'API tourne sur `localhost:8000`. Pour RapidAPI, elle doit être accessible
sur une URL publique HTTPS.

Option A — avec domaine custom (recommandé si tu as un domaine) :
Mets à jour le `Caddyfile` à la racine du projet :

```
api.tsfa.io {
    reverse_proxy localhost:8000
    encode gzip
    header {
        -Server
        X-Content-Type-Options nosniff
        X-Frame-Options DENY
    }
}
```

Option B — sans domaine, avec IP directe :
RapidAPI accepte une URL HTTP/HTTPS directe avec IP. Configure Caddy
pour servir sur le port 443 avec un certificat auto-signé, ou utilise
simplement l'IP:port en HTTP pour commencer (RapidAPI supporte les deux).

Dans tous les cas, génère le fichier `Caddyfile` final fonctionnel
et redémarre Caddy :

```bash
sudo systemctl reload caddy
# Vérifie :
curl https://api.tsfa.io/health  # ou http://IP:8000/health
```

---

### 3. docker-compose — configuration production finale

Mets à jour `docker-compose.yml` pour la prod :

```yaml
version: '3.9'

services:
  api:
    build: .
    restart: always          # redémarre automatiquement après crash ou reboot
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  redis:
    image: redis:7-alpine
    restart: always
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    volumes:
      - redis_data:/data     # persistance Redis entre redémarrages

volumes:
  redis_data:
```

Active le démarrage automatique au boot du VPS :

```bash
sudo systemctl enable docker
docker-compose up -d
```

---

### 4. Script de déploiement — automatise les mises à jour futures

Crée `scripts/deploy.sh` :

```bash
#!/bin/bash
set -e

echo "=== TSFA Deploy ==="
echo "Pulling latest code..."
git pull origin main

echo "Building new image..."
docker-compose build --no-cache api

echo "Running tests..."
docker-compose run --rm api pytest tests/ -x -q

echo "Deploying..."
docker-compose up -d --force-recreate api

echo "Waiting for health check..."
sleep 5
curl -f http://localhost:8000/health || (echo "Health check failed!" && exit 1)

echo "=== Deploy complete ==="
```

```bash
chmod +x scripts/deploy.sh
```

---

### 5. HuggingFace Hub — publication du modèle et benchmarks

Crée `scripts/publish_huggingface.py` :

Ce script publie sur HuggingFace Hub :
- Un README.md formaté avec les benchmarks (depuis `benchmarks/results/README.md`)
- Le fichier `benchmark_results.json`
- Un notebook d'exemple (`docs/examples/notebook_example.ipynb` si existant)
- Un lien vers l'API RapidAPI dans la description

```python
"""
Publication sur HuggingFace Hub.
Usage : python scripts/publish_huggingface.py --repo dorianmrt/tsfa-forecasting-api

Nécessite : pip install huggingface_hub
            huggingface-cli login
"""
from huggingface_hub import HfApi, upload_file, create_repo
import argparse

def publish(repo_id: str):
    api = HfApi()

    # Crée le repo si inexistant
    create_repo(repo_id, repo_type="model", exist_ok=True)

    # README principal avec benchmarks intégrés
    readme_content = generate_readme()
    # ...

def generate_readme() -> str:
    """
    Génère un README.md HuggingFace qui inclut :
    - Description de TSFA
    - Lien RapidAPI (placeholder à remplir après publication)
    - Tableau des benchmarks depuis benchmark_results.json
    - Exemple de code Python
    - Métriques : MAE, RMSE, MAPE, sMAPE sur M5/ETT/Exchange Rate
    """
```

---

### 6. Fichiers de publication RapidAPI — version finale

Génère les fichiers suivants prêts à copier-coller dans l'interface RapidAPI :

**`docs/rapidapi/api_description.md`** — description longue (max 2000 chars) :
Rédige en anglais, orienté développeur. Inclut :
- Ce que fait l'API en 2 phrases
- 3 use cases concrets (inventory, energy, finance)
- Les 3 modèles disponibles (ARIMA, Chronos, LSTM) avec leurs forces
- Un lien vers les benchmarks HuggingFace (placeholder)
- "Zero setup required"

**`docs/rapidapi/endpoint_descriptions.md`** — descriptions courtes par endpoint :
```
POST /forecast/univariate : Forecast a single time series. Supports AutoARIMA, Chronos-T5 and LSTM models with calibrated confidence intervals.
POST /forecast/batch      : Forecast 50-500 time series in parallel. Pro/Ultra plans only.
POST /validate            : Backtest your forecasting model with sliding window cross-validation.
GET  /models              : List available models and their capabilities.
GET  /usage               : Check your credit usage for the current billing period.
GET  /health              : API health status and connectivity check.
```

**`docs/rapidapi/tags.txt`** — tags RapidAPI (max 5) :
```
time-series, forecasting, machine-learning, prediction, arima
```

---

### 7. Tests finaux avant publication

**`tests/integration/test_production_readiness.py`** — nouveau fichier :

```python
"""
Tests de readiness production.
Ces tests vérifient les comportements critiques pour RapidAPI.
"""

def test_proxy_secret_missing_returns_403_in_production():
    """Sans X-RapidAPI-Proxy-Secret en mode production → 403"""

def test_proxy_secret_valid_passes():
    """Avec le bon secret → requête traitée normalement"""

def test_response_headers_present():
    """X-Request-Id, X-Credits-Used, X-Credits-Remaining présents"""

def test_oversized_series_rejected():
    """Série de 50001 valeurs → 422"""

def test_health_returns_all_fields():
    """Health check contient status, version, modal_connected, redis_connected, uptime_seconds"""

def test_gzip_compression_active():
    """Réponse avec Accept-Encoding: gzip → contenu compressé"""

def test_rate_limit_headers_present():
    """X-RateLimit-Limit et X-RateLimit-Remaining présents sur toutes les réponses"""
```

**Cible finale : 165+ tests, tous verts.**

---

### 8. Checklist publication RapidAPI — génère un fichier de suivi

Crée `docs/rapidapi/publication_checklist.md` :

```markdown
# RapidAPI Publication Checklist

## Pré-requis techniques
- [ ] URL publique HTTPS accessible depuis internet
- [ ] GET /health retourne 200 depuis l'extérieur
- [ ] X-RapidAPI-Proxy-Secret configuré dans .env ET dans l'interface RapidAPI
- [ ] Tous les endpoints documentés avec exemples

## Interface RapidAPI — étapes dans l'ordre
- [ ] Créer un compte Provider sur rapidapi.com/provider
- [ ] New API → choisir "REST API"
- [ ] Base URL : https://api.tsfa.io (ou http://IP:8000)
- [ ] Importer le schéma OpenAPI : GET http://localhost:8000/openapi.json
- [ ] Vérifier que tous les endpoints sont détectés
- [ ] Configurer les plans tarifaires (Free/Basic/Pro/Ultra)
- [ ] Copier api_description.md dans la description longue
- [ ] Ajouter les tags depuis tags.txt
- [ ] Configurer X-RapidAPI-Proxy-Secret (onglet Security)
- [ ] Tester chaque endpoint depuis l'interface RapidAPI (Test tab)
- [ ] Soumettre pour review RapidAPI (24-48h)

## Post-publication
- [ ] Publier modèle sur HuggingFace Hub (python scripts/publish_huggingface.py)
- [ ] Ajouter le lien RapidAPI dans le README HuggingFace
- [ ] Tester un appel réel depuis RapidAPI avec une vraie API key
- [ ] Vérifier que les crédits sont décomptés correctement
```

---

## CONTRAINTES STRICTES

- ❌ Ne pas ajouter de nouvelles fonctionnalités ML
- ❌ Ne pas modifier la logique des endpoints existants
- ✅ Aucune régression sur les 154 tests existants
- ✅ ENVIRONMENT=development dans les tests (proxy secret non vérifié)
- ✅ ENVIRONMENT=production dans .env sur le VPS
- ✅ Tout le code committé et pushé sur Git avant la fin

---

## ORDRE D'EXÉCUTION

1. Audit sécurité : proxy secret, payload limits, logs (pas de données sensibles)
2. Génère SECRET_KEY et mets à jour .env
3. Mets à jour docker-compose.yml (restart: always, healthchecks, volume Redis)
4. Configure Caddyfile final + reload Caddy
5. Crée scripts/deploy.sh
6. Écris les tests de production readiness → tous verts
7. Génère les fichiers docs/rapidapi/ finaux
8. Crée scripts/publish_huggingface.py
9. Lance pytest complet → 165+ verts
10. Lance scripts/deploy.sh pour valider le flow de déploiement complet
11. Génère docs/rapidapi/publication_checklist.md
12. Commit + push tout sur Git

---

## VALIDATION FINALE

```bash
# Depuis l'extérieur du VPS (ta machine locale) :
curl https://api.tsfa.io/health
# ou
curl http://IP_VPS:8000/health
# Doit retourner 200 avec modal_connected et redis_connected

# Depuis le VPS, simule un appel RapidAPI avec proxy secret :
curl -X POST http://localhost:8000/v1/forecast/univariate \
  -H "Content-Type: application/json" \
  -H "X-Plan: pro" \
  -H "X-RapidAPI-User: test-user-pub" \
  -H "X-RapidAPI-Proxy-Secret: $(grep RAPIDAPI_PROXY_SECRET .env | cut -d= -f2)" \
  -d '{"series":[120,132,128,145,139,152,148,160,155,168,163,175,170,182],"horizon":7,"model":"chronos"}'
# Doit retourner model_used: chronos-t5-small avec les headers X-Credits-*

# Sans le proxy secret (simule un appel direct bypass) :
curl -X POST http://localhost:8000/v1/forecast/univariate \
  -H "Content-Type: application/json" -H "X-Plan: pro" \
  -d '{"series":[120,132,128,145,139,152],"horizon":3,"model":"arima"}'
# En mode ENVIRONMENT=production → doit retourner HTTP 403
```

**Cible : 165+ tests verts + appel externe HTTPS 200 + 403 sans proxy secret
= API prête pour publication RapidAPI.**
