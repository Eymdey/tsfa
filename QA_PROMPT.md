# TSFA — Prompt QA Complet : Validation avant mise en avant publique

## CONTEXTE

L'API est publiée sur RapidAPI, le code est sur GitHub, 165 tests passent.
Avant toute acquisition d'utilisateurs ou publication marketing, on valide
que tout ce qu'un développeur externe va voir, tester, et lire est irréprochable.

Ce prompt ne construit rien de nouveau. Il audite, corrige, et produit
des assets marketing réutilisables (use cases concrets, notebooks, tutoriels).

Relis `project-context.md` et `project-specs.md` avant de commencer.

---

## PARTIE 1 — AUDIT FONCTIONNEL COMPLET

### 1.1 Vérification de chaque endpoint en conditions réelles

Lance ces tests manuels dans l'ordre et documente chaque résultat.
Pour chaque curl : note le status HTTP, le `model_used`, la cohérence
des valeurs de `forecast.mean`, et le temps de réponse `inference_time_ms`.

```bash
# ── TEST 1 : AutoARIMA univarié (série courte, modèle forcé)
curl -s -w "\nHTTP %{http_code} — %{time_total}s\n" \
  -X POST http://localhost:8000/v1/forecast/univariate \
  -H "Content-Type: application/json" \
  -H "X-Plan: basic" \
  -H "X-RapidAPI-Proxy-Secret: $(grep RAPIDAPI_PROXY_SECRET .env | cut -d= -f2)" \
  -d '{
    "series": [100,102,98,105,103,107,104,109,106,111],
    "horizon": 5,
    "frequency": "D",
    "model": "arima"
  }' | python3 -m json.tool

# Attendu : model_used=arima, 5 valeurs croissantes/stables autour de 110-115

# ── TEST 2 : Chronos univarié (série longue avec saisonnalité)
curl -s -w "\nHTTP %{http_code} — %{time_total}s\n" \
  -X POST http://localhost:8000/v1/forecast/univariate \
  -H "Content-Type: application/json" \
  -H "X-Plan: pro" \
  -H "X-RapidAPI-Proxy-Secret: $(grep RAPIDAPI_PROXY_SECRET .env | cut -d= -f2)" \
  -d '{
    "series": [100,110,120,115,105,100,110,120,115,105,100,110,
               120,115,105,100,110,120,115,105,100,110,120,115,
               105,100,110,120,115,105,100,110,120,115,105,100],
    "horizon": 14,
    "frequency": "D",
    "model": "chronos",
    "confidence_levels": [0.8, 0.95]
  }' | python3 -m json.tool

# Attendu : model_used=chronos-t5-small, saisonnalité détectée dans diagnostics,
#           intervalles lower_80/upper_80/lower_95/upper_95 tous présents et
#           lower_95 < lower_80 < mean < upper_80 < upper_95 sur chaque point

# ── TEST 3 : Auto-selection (série >= 30 obs, horizon <= 90) → doit choisir Chronos
curl -s -X POST http://localhost:8000/v1/forecast/univariate \
  -H "Content-Type: application/json" \
  -H "X-Plan: pro" \
  -H "X-RapidAPI-Proxy-Secret: $(grep RAPIDAPI_PROXY_SECRET .env | cut -d= -f2)" \
  -d '{
    "series": [50,52,49,54,53,55,51,56,54,57,53,58,55,59,56,60,
               57,61,58,62,59,63,60,64,61,65,62,66,63,67,64,68],
    "horizon": 7,
    "frequency": "D",
    "model": "auto"
  }' | python3 -m json.tool | grep "model_used"

# Attendu : "model_used": "chronos-t5-small"

# ── TEST 4 : LSTM (horizon long > 90 jours)
curl -s -X POST http://localhost:8000/v1/forecast/univariate \
  -H "Content-Type: application/json" \
  -H "X-Plan: ultra" \
  -H "X-RapidAPI-Proxy-Secret: $(grep RAPIDAPI_PROXY_SECRET .env | cut -d= -f2)" \
  -d '{
    "series": [50,52,49,54,53,55,51,56,54,57,53,58,55,59,56,60,
               57,61,58,62,59,63,60,64,61,65,62,66,63,67,64,68,
               65,69,66,70,67,71,68,72,69,73,70,74,71,75,72,76,
               73,77,74,78],
    "horizon": 120,
    "frequency": "D",
    "model": "auto"
  }' | python3 -m json.tool | grep -E "model_used|inference_time"

# Attendu : model_used=lstm, inference_time_ms raisonnable (<10000ms)

# ── TEST 5 : Validate — backtesting réel
curl -s -X POST http://localhost:8000/v1/validate \
  -H "Content-Type: application/json" \
  -H "X-Plan: pro" \
  -H "X-RapidAPI-Proxy-Secret: $(grep RAPIDAPI_PROXY_SECRET .env | cut -d= -f2)" \
  -d '{
    "series": [100,102,98,105,103,107,104,109,106,111,108,113,
               110,115,112,117,114,119,116,121,118,123,120,125,
               122,127,124,129,126,131,128,133,130,135,132,137,
               134,139,136,141,138,143,140,145,142,147,144,149],
    "horizon": 7,
    "frequency": "D",
    "model": "arima",
    "n_windows": 3
  }' | python3 -m json.tool

# Attendu : mae/rmse/mape cohérents, coverage_80 entre 0.7-0.9,
#           coverage_95 entre 0.85-1.0, 3 windows dans le détail

# ── TEST 6 : Batch — 3 séries en parallèle
curl -s -X POST http://localhost:8000/v1/forecast/batch \
  -H "Content-Type: application/json" \
  -H "X-Plan: pro" \
  -H "X-RapidAPI-Proxy-Secret: $(grep RAPIDAPI_PROXY_SECRET .env | cut -d= -f2)" \
  -d '{
    "series_list": [
      {"id": "store_A", "values": [200,210,195,215,205,220,210,225,215,230,220,235,225,240,230,245], "horizon": 7},
      {"id": "store_B", "values": [500,510,490,515,505,520,510,525,515,530,520,535,525,540,530,545], "horizon": 7},
      {"id": "store_C", "values": [50,52,49,54,53,55,51,56,54,57,53,58,55,59,56,60,57,61,58,62], "horizon": 7}
    ],
    "frequency": "D",
    "model": "arima"
  }' | python3 -m json.tool

# Attendu : 3 résultats, chacun avec forecast.mean de 7 valeurs,
#           inference_time total < 3x le temps d'un appel unique

# ── TEST 7 : Erreurs — validation inputs
echo "=== Série trop courte ==="
curl -s -o /dev/null -w "%{http_code}" \
  -X POST http://localhost:8000/v1/forecast/univariate \
  -H "Content-Type: application/json" -H "X-Plan: free" \
  -d '{"series": [1,2,3], "horizon": 5, "frequency": "D"}'
# Attendu : 422

echo "=== Batch sur plan free ==="
curl -s -o /dev/null -w "%{http_code}" \
  -X POST http://localhost:8000/v1/forecast/batch \
  -H "Content-Type: application/json" -H "X-Plan: free" \
  -d '{"series_list": [{"id":"x","values":[1,2,3,4,5,6,7,8,9,10],"horizon":3}],"frequency":"D"}'
# Attendu : 403

echo "=== Sans proxy secret (mode production) ==="
curl -s -o /dev/null -w "%{http_code}" \
  -X POST http://localhost:8000/v1/forecast/univariate \
  -H "Content-Type: application/json" -H "X-Plan: free" \
  -d '{"series": [1,2,3,4,5,6,7,8,9,10], "horizon": 3, "frequency": "D"}'
# Attendu : 403

# ── TEST 8 : Headers de réponse
curl -sI -X POST http://localhost:8000/v1/forecast/univariate \
  -H "Content-Type: application/json" -H "X-Plan: free" \
  -H "X-RapidAPI-Proxy-Secret: $(grep RAPIDAPI_PROXY_SECRET .env | cut -d= -f2)" \
  -d '{"series":[1,2,3,4,5,6,7,8,9,10],"horizon":3,"frequency":"D","model":"arima"}' \
  | grep -E "X-Request-Id|X-Credits|X-RateLimit"
# Attendu : les 4 headers présents avec valeurs numériques
```

### 1.2 Vérification de la cohérence mathématique des intervalles

Pour chaque réponse avec intervalles de confiance, vérifie automatiquement :

```python
# Crée scripts/verify_intervals.py
"""
Vérifie que les intervalles de confiance sont mathématiquement corrects
sur les réponses réelles de l'API.
"""
import requests
import json

def verify_response(response: dict) -> list[str]:
    """
    Retourne une liste d'anomalies. Liste vide = tout est correct.
    Vérifie :
    - lower_95 <= lower_80 <= mean <= upper_80 <= upper_95 pour chaque pas
    - Aucune valeur NaN ou Infinity
    - Longueur forecast == horizon demandé
    - mean est dans [lower_95, upper_95] pour chaque pas
    """
    errors = []
    forecast = response.get("forecast", {})
    mean = forecast.get("mean", [])
    l80 = forecast.get("lower_80", [])
    u80 = forecast.get("upper_80", [])
    l95 = forecast.get("lower_95", [])
    u95 = forecast.get("upper_95", [])

    for i, (m, lb, ub, l9, u9) in enumerate(zip(mean, l80, u80, l95, u95)):
        if not (l9 <= lb <= m <= ub <= u9):
            errors.append(f"Step {i}: interval ordering violated: {l9:.2f} <= {lb:.2f} <= {m:.2f} <= {ub:.2f} <= {u9:.2f}")
        if any(v != v for v in [m, lb, ub, l9, u9]):  # NaN check
            errors.append(f"Step {i}: NaN detected")

    return errors

# Teste sur 5 séries différentes et affiche un rapport
```

Lance ce script et corrige toute anomalie avant de continuer.

---

## PARTIE 2 — AUDIT DOCUMENTATION

### 2.1 README.md — audit complet

Lis `README.md` et vérifie que chaque commande documentée fonctionne réellement.
Pour chaque section :

**Installation :**
```bash
# Clone un dossier temporaire et teste l'install from scratch
mkdir /tmp/tsfa-test && cd /tmp/tsfa-test
git clone https://github.com/Eymdey/tsfa.git .
cp .env.example .env
# Remplis les valeurs minimales dans .env
docker-compose up -d
sleep 10
curl http://localhost:8001/health  # port différent pour éviter conflit
```

Si ça ne marche pas → corrige le README ET le code jusqu'à ce que ça marche.

**Mets à jour README.md avec :**
- Badge GitHub Actions (si CI configuré) ou badge "Tests: 165 passing"
- Badge "Available on RapidAPI" avec lien direct
- Section "Benchmarks" avec tableau depuis `benchmarks/results/README.md`
- Section "Quick Start" avec le curl le plus simple possible (plan free, ARIMA)
- Section "Models" claire avec tableau comparatif
- Lien vers la documentation complète

### 2.2 docs/quickstart.md — vérification complète

Lis ce fichier et joue chaque étape exactement comme un développeur externe le ferait.
Corrige tout ce qui est imprécis, manquant, ou qui ne fonctionne pas.

Le quickstart doit permettre à un dev qui ne connaît pas le projet d'obtenir
sa première prédiction en moins de 5 minutes. Vérifie :
- Les exemples de code fonctionnent tels quels (copy-paste → ça marche)
- Les valeurs d'exemple dans les requêtes retournent des résultats sensés
- Les messages d'erreur documentés correspondent aux vraies erreurs retournées

### 2.3 docs/examples/ — vérification et correction

**`python_example.py`** : exécute-le et vérifie qu'il tourne sans erreur :
```bash
cd ~/tsfa
python3 docs/examples/python_example.py
```

**`curl_example.sh`** : exécute chaque commande et vérifie les réponses :
```bash
chmod +x docs/examples/curl_example.sh
bash docs/examples/curl_example.sh
```

Corrige tout exemple qui ne fonctionne pas ou qui retourne une erreur.

### 2.4 OpenAPI Schema — audit qualité

```bash
curl http://localhost:8000/openapi.json | python3 -m json.tool > /tmp/schema_check.json
```

Vérifie dans le schéma OpenAPI :
- Chaque endpoint a une `description` non vide
- Chaque paramètre a un `description` et un `example`
- Les réponses d'erreur (422, 403, 429, 503) sont documentées
- Le `title` de l'API et la `description` globale sont renseignés et professionnels

Si des descriptions manquent → ajoute-les dans les routers FastAPI avec
`summary=`, `description=`, et `responses=` sur les décorateurs.

---

## PARTIE 3 — BENCHMARKS : VÉRIFICATION ET MISE EN VALEUR

### 3.1 Vérifie que les benchmarks sont reproductibles

```bash
cd ~/tsfa
python3 benchmarks/run_benchmark.py --model arima --output /tmp/bench_verify/
```

Compare les résultats avec `benchmarks/results/benchmark_results.json`.
Les métriques doivent être identiques (±1% de variance acceptable).

Si elles diffèrent → le benchmark n'est pas reproductible, c'est un problème
de crédibilité majeur. Diagnostique et corrige (seed aléatoire, version de lib).

### 3.2 Ajoute une comparaison avec baseline naïve

Dans `benchmarks/run_benchmark.py`, ajoute un modèle `naive` :
- **Naive** : prédit la dernière valeur connue pour tous les horizons
- **Seasonal Naive** : prédit la valeur du même jour la semaine précédente

Ces baselines doivent apparaître dans le tableau final pour montrer
que TSFA bat significativement le "rien faire".

Tableau attendu dans `benchmarks/results/README.md` :

```markdown
## Results on M5 Sample Dataset (horizon=7, frequency=D)

| Model          | MAE    | RMSE   | MAPE   | sMAPE  |
|----------------|--------|--------|--------|--------|
| Naive          | 15.2   | 18.4   | 12.1%  | 11.8%  |
| Seasonal Naive | 11.8   | 14.2   | 9.4%   | 9.1%   |
| **AutoARIMA**  | 9.04   | 10.56  | 7.63%  | 7.43%  |
| **Chronos**    | X.XX   | X.XX   | X.XX%  | X.XX%  |

*Lower is better. Benchmarks run on public datasets with fixed random seed 42.*
```

---

## PARTIE 4 — USE CASES CONCRETS POUR LA MISE EN AVANT

C'est la partie la plus importante pour l'acquisition. Chaque use case
doit être un fichier autonome, reproductible, avec des données réelles
ou réalistes, et un résultat visuel clair.

### 4.1 Use Case 1 — Prévision de ventes retail (E-commerce)

Crée `docs/use_cases/01_retail_demand_forecasting.ipynb` :

```
Titre : "Forecast product demand with 3 lines of code"

Contexte :
  Un e-commerce veut prévoir les ventes des 14 prochains jours pour
  optimiser ses stocks. Il a 6 mois d'historique de ventes journalières.

Données :
  Génère une série synthétique réaliste :
  - Tendance haussière légère (+0.5%/semaine)
  - Saisonnalité hebdomadaire (pics vendredi-samedi)
  - Bruit gaussien raisonnable
  - 180 observations (6 mois de données journalières)

Structure du notebook :
  1. Génération des données (commenté : "In production, replace with your CSV")
  2. Appel API TSFA (plan Free suffit pour cet exemple)
  3. Visualisation matplotlib : historique + prévision + intervalles de confiance
     (graphe propre avec couleurs distinctes, titre, légende)
  4. Calcul du bénéfice métier : "With 95% CI, plan stock between X and Y units"
  5. Résultat attendu : graphe PNG sauvegardé dans docs/use_cases/outputs/
```

### 4.2 Use Case 2 — Détection de tendance financière

Crée `docs/use_cases/02_financial_trend_forecasting.ipynb` :

```
Titre : "Forecast currency exchange rates for risk management"

Contexte :
  Une fintech veut prévoir le taux EUR/USD sur 30 jours pour
  alerter ses clients sur les risques de change.

Données :
  Utilise les vraies données Exchange Rate du benchmark (déjà téléchargées).
  Prends les 200 dernières observations comme historique.

Structure du notebook :
  1. Chargement des données réelles depuis benchmarks/datasets/
  2. Appel API avec model="auto" (doit sélectionner Chronos)
  3. Visualisation avec bandes de confiance
  4. Calcul : "90% probability the rate stays between X and Y"
  5. Comparaison visuelle : ARIMA vs Chronos sur les mêmes données
```

### 4.3 Use Case 3 — Prévision de consommation énergétique

Crée `docs/use_cases/03_energy_consumption_forecasting.ipynb` :

```
Titre : "Predict energy consumption for smart grid optimization"

Contexte :
  Un gestionnaire de réseau électrique prédit la consommation
  des 48 prochaines heures pour optimiser la production.

Données :
  Utilise les données ETT-h1 du benchmark (déjà téléchargées).
  Fréquence horaire, 30 jours d'historique = 720 observations.

Structure du notebook :
  1. Chargement ETT-h1
  2. Appel API avec frequency="H", model="lstm" (horizon > 90h)
  3. Visualisation heure par heure
  4. Métriques de qualité (backtest avec /validate)
  5. Conclusion : "TSFA achieves X% MAPE on energy data"
```

### 4.4 Use Case 4 — Batch forecasting pour SaaS multi-tenant

Crée `docs/use_cases/04_batch_forecasting_saas.py` (script Python, pas notebook) :

```python
"""
Use Case : SaaS platform forecasting 50 product lines simultaneously.
Demonstrates batch endpoint efficiency vs. 50 individual calls.

This example shows:
- How to use /forecast/batch for high-volume forecasting
- Time comparison: batch vs sequential calls
- Error handling when one series is malformed
"""
```

Inclut un vrai timer et affiche la comparaison :
```
Sequential (50 calls) : X.Xs
Batch (1 call)        : X.Xs
Speedup               : Xx faster
```

### 4.5 Génère les graphiques PNG pour chaque use case

Pour chaque notebook, génère et sauvegarde les graphiques finaux dans
`docs/use_cases/outputs/` :
- `01_retail_forecast.png`
- `02_financial_forecast.png`
- `03_energy_forecast.png`

Ces images seront utilisées directement dans les posts Reddit, HuggingFace,
et la page RapidAPI. Elles doivent être propres, professionnelles :
- Fond blanc
- Titre descriptif
- Axe x = dates lisibles
- Légende claire (Historical / Forecast / 80% CI / 95% CI)
- Couleurs cohérentes (bleu pour historique, orange pour forecast, gris pour CI)
- DPI 150 minimum

---

## PARTIE 5 — RAPPORT FINAL QA

À la fin de tout ce qui précède, génère `docs/QA_REPORT.md` :

```markdown
# TSFA Quality Assurance Report
Generated : {date}

## API Functional Tests
| Test | Status | HTTP | model_used | inference_ms |
|------|--------|------|------------|--------------|
| Univariate ARIMA | ✅ | 200 | arima | Xms |
| Univariate Chronos | ✅ | 200 | chronos-t5-small | Xms |
| Auto-selection → Chronos | ✅ | 200 | chronos-t5-small | Xms |
| Auto-selection → LSTM | ✅ | 200 | lstm | Xms |
| Validate backtest | ✅ | 200 | arima | Xms |
| Batch 3 series | ✅ | 200 | arima | Xms |
| Error: series too short | ✅ | 422 | - | - |
| Error: batch on free plan | ✅ | 403 | - | - |
| Error: no proxy secret | ✅ | 403 | - | - |

## Interval Coherence Check
| Model | Series tested | Violations |
|-------|--------------|------------|
| ARIMA | 10 | 0 |
| Chronos | 10 | 0 |

## Documentation Tests
| File | Executable | Errors |
|------|-----------|--------|
| docs/examples/python_example.py | ✅ | 0 |
| docs/examples/curl_example.sh | ✅ | 0 |
| docs/quickstart.md | ✅ verified | 0 |

## Benchmark Reproducibility
| Dataset | Expected MAE | Actual MAE | Delta |
|---------|-------------|------------|-------|
| ETT-h1 | 2.4524 | X.XXXX | X% |
| Exchange Rate | 0.0085 | X.XXXX | X% |
| M5 Sample | 9.0427 | X.XXXX | X% |

## Use Cases Generated
- [x] 01_retail_demand_forecasting.ipynb + PNG
- [x] 02_financial_trend_forecasting.ipynb + PNG
- [x] 03_energy_consumption_forecasting.ipynb + PNG
- [x] 04_batch_forecasting_saas.py

## Known Issues
{liste tout problème trouvé et son statut : fixed / acceptable / backlog}

## Verdict
✅ READY FOR PUBLIC PROMOTION
```

---

## CONTRAINTES STRICTES

- ❌ Ne pas modifier la logique des endpoints
- ❌ Ne pas casser les 165 tests existants
- ✅ Corriger TOUT ce qui ne fonctionne pas dans la documentation
- ✅ Les use cases doivent tourner avec l'API réelle (pas de mock)
- ✅ Les graphiques PNG doivent être générés et sauvegardés
- ✅ Le QA_REPORT.md doit refléter les vrais résultats, pas des valeurs inventées
- ✅ Commit et push tout à la fin : `git add -A && git commit -m "QA: full audit + use cases + benchmarks" && git push`

---

## ORDRE D'EXÉCUTION

1. Partie 1 — lance tous les curls de test, note les résultats
2. Lance `scripts/verify_intervals.py` sur 5 séries
3. Partie 2 — audit README + quickstart + exemples + OpenAPI
4. Partie 3 — vérifie reproductibilité benchmarks, ajoute baseline naïve
5. Partie 4 — crée les 4 use cases + génère les 3 PNG
6. Partie 5 — génère QA_REPORT.md avec les vrais résultats
7. Lance pytest → 165+ verts
8. Commit + push

---

## VALIDATION FINALE

Le QA est terminé quand :
- `docs/QA_REPORT.md` existe avec le verdict **✅ READY FOR PUBLIC PROMOTION**
- Les 3 fichiers PNG existent dans `docs/use_cases/outputs/`
- `pytest` passe toujours à 165+ verts
- Aucun exemple dans la documentation ne retourne une erreur quand exécuté
