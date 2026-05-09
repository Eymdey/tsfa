# RapidAPI Publication Checklist

## Pré-requis techniques

- [ ] URL publique HTTPS accessible depuis internet (`curl https://api.tsfa.io/health`)
- [ ] GET /health retourne 200 avec `redis_connected: true`
- [ ] `X-RapidAPI-Proxy-Secret` configuré dans `.env` ET dans l'interface RapidAPI
- [ ] `ENVIRONMENT=production` dans `.env` sur le VPS
- [ ] Sans proxy secret → 403 (`curl` direct sans header → doit échouer)
- [ ] Tous les endpoints documentés avec exemples dans OpenAPI (`/docs`)
- [ ] 165+ tests verts (`pytest --tb=short`)

## Interface RapidAPI — étapes dans l'ordre

- [ ] Créer un compte Provider sur rapidapi.com/provider
- [ ] New API → choisir "REST API"
- [ ] Base URL : `https://api.tsfa.io` (ou `http://IP:8000`)
- [ ] Importer le schéma OpenAPI : `GET http://localhost:8000/openapi.json`
- [ ] Vérifier que tous les endpoints sont détectés (6 endpoints)
- [ ] Configurer les plans tarifaires (Free / Basic / Pro / Ultra)
  - Free : 100 crédits/mois, 10 req/min, $0
  - Basic : 1 000 crédits/mois, 30 req/min, $9
  - Pro : 10 000 crédits/mois, 100 req/min, $29
  - Ultra : 100 000 crédits/mois, 500 req/min, $99
- [ ] Copier `docs/rapidapi/api_description.md` dans la description longue
- [ ] Ajouter les tags depuis `docs/rapidapi/tags.txt`
- [ ] Configurer `X-RapidAPI-Proxy-Secret` dans l'onglet Security
- [ ] Tester chaque endpoint depuis l'interface RapidAPI (Test tab)
  - [ ] POST /v1/forecast/univariate → 200 avec forecast.mean
  - [ ] POST /v1/forecast/batch → 200 (Pro plan)
  - [ ] POST /v1/validate → 200 avec mae/rmse/mape
  - [ ] GET /v1/models → 200 avec liste modèles
  - [ ] GET /v1/usage → 200 avec credits_used
  - [ ] GET /health → 200
- [ ] Vérifier que `X-Credits-Used` et `X-Credits-Remaining` sont dans les réponses
- [ ] Soumettre pour review RapidAPI (délai : 24–48h)

## Post-publication

- [ ] Récupérer l'URL RapidAPI définitive
- [ ] Mettre à jour `RAPIDAPI_URL` dans `scripts/publish_huggingface.py`
- [ ] Publier sur HuggingFace Hub : `python scripts/publish_huggingface.py`
- [ ] Ajouter le lien RapidAPI dans le README HuggingFace
- [ ] Tester un appel réel depuis RapidAPI avec une vraie API key
- [ ] Vérifier que les crédits sont décomptés correctement dans `/v1/usage`
- [ ] Configurer les alertes monitoring (Grafana / UptimeRobot)
- [ ] Vérifier les logs (`docker-compose logs -f api`)

## Validation finale

```bash
# Depuis l'extérieur du VPS :
curl https://api.tsfa.io/health
# → {"status":"ok","version":"1.0.0","redis_connected":true,"uptime_seconds":...}

# Appel RapidAPI avec proxy secret :
curl -X POST http://localhost:8000/v1/forecast/univariate \
  -H "Content-Type: application/json" \
  -H "X-Plan: pro" \
  -H "X-RapidAPI-Proxy-Secret: $(grep RAPIDAPI_PROXY_SECRET .env | cut -d= -f2)" \
  -d '{"series":[120,132,128,145,139,152,148,160,155,168],"horizon":7,"model":"chronos"}'
# → model_used: chronos-t5-small, X-Credits-Used: 1

# Sans proxy secret (bypass check) :
curl -X POST http://localhost:8000/v1/forecast/univariate \
  -H "Content-Type: application/json" -H "X-Plan: pro" \
  -d '{"series":[120,132,128],"horizon":3}'
# → HTTP 403 {"code":"FORBIDDEN"}
```

---

*Généré le 2026-05-09*
