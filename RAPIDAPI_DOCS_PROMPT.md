# TSFA — Prompt Documentation RapidAPI + Site Web

## CONTEXTE

L'API est techniquement complète et prête (165 tests verts, Modal déployé,
tous les endpoints fonctionnels). Elle est en attente de publication sur RapidAPI.

Avant de soumettre, RapidAPI demande plusieurs éléments de contenu que tu dois
générer en lisant l'intégralité du projet (code, benchmarks, specs, README existant).

Le domaine du projet est : **eymdey-network.com**
Le workspace RapidAPI est : **dorianmrt**
Les benchmarks sont dans : `benchmarks/results/benchmark_results.json`
et `benchmarks/results/README.md`

Tu vas générer TOUS les fichiers de contenu RapidAPI dans `docs/rapidapi/final/`.

---

## PRICING À VALIDER EN PREMIER

Avant de générer quoi que ce soit, analyse le pricing suivant choisi par le
propriétaire et évalue s'il est cohérent avec :
- Les plans définis dans project-specs.md
- Les limites de crédits implémentées dans le code (config.py, credits.py)
- Le positionnement marché défini dans project-context.md

Pricing choisi :
```
BASIC  : $0.00/month  — 100 requests/month
PRO    : $49.00/month — 10 000 requests/month
ULTRA  : $199.00/month — 50 000 requests/month
MEGA   : $499.00/month — 200 000 requests/month
```

Produis un fichier `docs/rapidapi/final/pricing_analysis.md` qui :
1. Compare ce pricing avec les specs initiales (qui prévoyait Free/Basic/Pro/Ultra)
2. Identifie les incohérences éventuelles avec le code (noms de plans, limites)
3. Liste les fichiers de code à mettre à jour si le nom des plans change
   (ex: "basic" → "basic" gratuit, "pro" → "pro" payant, etc.)
4. Donne une recommandation claire : adopter tel quel ou ajuster

---

## FICHIERS À GÉNÉRER

Tous les fichiers vont dans `docs/rapidapi/final/`. Crée ce dossier.
Chaque fichier doit être rédigé en **anglais**, orienté développeur,
professionnel mais direct. Pas de bullshit marketing.

---

### FICHIER 1 : `short_description.txt`

Maximum 100 caractères. Apparaît comme tagline sur le listing RapidAPI.

Contraintes :
- Pas de "AI-powered" ou "revolutionary" (trop générique)
- Doit mentionner ce que ça fait concrètement
- Doit donner envie à un dev de cliquer

Exemples de ce qu'il ne faut PAS faire :
- "The best time series API on the market" ❌
- "AI-powered forecasting solution" ❌

Ce qu'il faut viser :
- Concrète, technique, différenciante ✅

---

### FICHIER 2 : `long_description.md`

Apparaît sous la short description sur l'onglet Endpoints. Markdown accepté.
Longueur : 400-600 mots. Pas plus.

Structure obligatoire :
```
## What is TSFA?
[2-3 phrases max — ce que ça fait, pour qui]

## Models
[Tableau markdown : Model | Type | Best for | Avg latency]
Remplis les latences moyennes depuis les benchmarks réels du projet.

## Benchmark Results
[Tableau markdown depuis benchmark_results.json :
Dataset | Model | MAE | RMSE | MAPE | sMAPE]
Uniquement les résultats réels du projet — pas de chiffres inventés.

## Use Cases
[3 use cases concrets avec exemple de série et contexte métier :
1. Retail demand forecasting
2. Energy consumption prediction  
3. Financial time series]

## Quick Start
[Bloc de code Python minimal — 10 lignes max — copié depuis
docs/examples/python_example.py et adapté pour RapidAPI]

## Pricing
[Tableau des 4 plans avec les vrais chiffres choisis :
BASIC/PRO/ULTRA/MEGA + requests/month]
```

---

### FICHIER 3 : `readme.md`

Le README qui apparaît dans l'onglet "About" de RapidAPI (le Hub README).
C'est le document le plus complet. Longueur : 800-1200 mots.

Structure obligatoire :

```markdown
# TSFA — Time Series Forecasting API

[Badge : version 1.0.0] [Badge : 165 tests] [Badge : Powered by Chronos-T5]

## Overview
## Why TSFA over alternatives
## Available Models
## API Endpoints
## Authentication
## Plans & Pricing
## Benchmark Results
## Code Examples (Python, JavaScript, cURL)
## Error Reference
## Changelog
## Support
```

**Section "Why TSFA over alternatives" — obligatoire :**
Compare honnêtement TSFA avec :
- AWS Forecast : prix, complexité setup
- Azure Time Series Insights : prix
- Nixtla TimeGPT : prix
- DIY (statsmodels/statsforecast) : temps de dev

Base-toi sur les vraies forces du projet : pricing, modèles disponibles,
zéro setup, intervalles de confiance calibrés, benchmarks publics.
Pas de fausses promesses — seulement ce que le code fait réellement.

**Section "Error Reference" — obligatoire :**
Liste tous les codes d'erreur définis dans le projet
(lis app/middleware/error_handler.py et les schemas pour les extraire) :
```
SERIES_TOO_SHORT | HORIZON_EXCEEDS_LIMIT | INVALID_FREQUENCY |
PLAN_REQUIRED | RATE_LIMIT_EXCEEDED | CREDITS_EXHAUSTED | etc.
```

---

### FICHIER 4 : `tutorial_01_quickstart.md`

Premier tutoriel — "Get your first forecast in 5 minutes".
Longueur : 300-400 mots, très orienté action.

Structure :
```
# Tutorial 1 : Your First Forecast in 5 Minutes

## Prerequisites
## Step 1 : Subscribe to TSFA on RapidAPI
## Step 2 : Make your first API call
[Code Python avec commentaires ligne par ligne]
## Step 3 : Understand the response
[JSON de réponse annoté — explique chaque champ]
## Step 4 : Choose the right model
[Tableau de décision simple : série courte → ARIMA, générale → Chronos, longue → LSTM]
## Next steps
```

---

### FICHIER 5 : `tutorial_02_batch_forecasting.md`

Deuxième tutoriel — "Forecast 50 products simultaneously".
Longueur : 300-400 mots.

Structure :
```
# Tutorial 2 : Batch Forecasting for Inventory Planning

## Use case
[Retailer avec 50 produits à prévoir chaque semaine]
## Requirements
[Plan PRO ou supérieur]
## Full Python example
[Code complet qui :
 1. Génère des données synthétiques pour 10 produits
 2. Envoie la requête batch
 3. Parse les résultats
 4. Affiche un résumé]
## Handling partial errors
[Montre comment gérer le cas où certaines séries échouent]
## Cost calculation
[Calcule combien de crédits consomme ce batch selon le plan]
```

---

### FICHIER 6 : `tutorial_03_backtesting.md`

Troisième tutoriel — "Validate your model before production".
Longueur : 250-350 mots.

Structure :
```
# Tutorial 3 : Backtesting — Validate Before You Commit

## Why backtest?
## The sliding window method
[Schéma ASCII simple montrant les fenêtres train/test]
## Full example
[Code Python qui :
 1. Envoie une série vers /validate
 2. Parse les métriques
 3. Décide si le modèle est acceptable (MAE < seuil)]
## Interpreting the metrics
[MAE, RMSE, MAPE, coverage_80, coverage_95 — ce que ça veut dire en pratique]
```

---

### FICHIER 7 : `spotlights.md`

RapidAPI permet d'ajouter des "spotlights" (points forts mis en avant).
Rédige 3 spotlights, chacun avec :
- Un titre (max 40 chars)
- Une description (max 120 chars)

Les 3 spotlights doivent couvrir :
1. Les modèles disponibles (Chronos, LSTM, ARIMA)
2. Les benchmarks publics
3. Le zero-setup / developer experience

---

### FICHIER 8 : `website_landing_page.html`

Une landing page HTML complète pour **eymdey-network.com/tsfa** (ou tsfa.eymdey-network.com).

Design : sobre, technique, crédible. Pas de couleurs flashy. Fond sombre ou blanc cassé.
Stack : HTML + CSS vanilla dans un seul fichier. Zéro dépendance externe.
Pas de JavaScript sauf pour la copie du code dans le clipboard.

Sections obligatoires :
```
1. Hero : titre + tagline + bouton "Get API Key on RapidAPI" (lien placeholder)
2. How it works : 3 étapes (Subscribe → Send data → Get forecast)
3. Models : tableau des 3 modèles avec caractéristiques
4. Benchmark Results : tableau depuis les vrais résultats du projet
5. Pricing : les 4 plans (BASIC/PRO/ULTRA/MEGA) avec boutons
6. Code example : snippet Python avec bouton "Copy"
7. Footer : lien GitHub, lien RapidAPI, contact
```

La page doit être **responsive** (mobile + desktop).
Elle sera hébergée sur le VPS Hetzner via Caddy.

---

### FICHIER 9 : `caddyfile_update.md`

Fournis la configuration Caddy mise à jour pour servir :
- `api.eymdey-network.com` → proxy vers localhost:8000 (l'API TSFA)
- `tsfa.eymdey-network.com` → sert la landing page HTML statique

Inclus les instructions DNS à configurer chez OVH :
```
Type A | Nom : api   | Valeur : IP_DU_VPS
Type A | Nom : tsfa  | Valeur : IP_DU_VPS
```

---

## CONTRAINTES STRICTES

- ✅ Tous les chiffres de benchmark doivent venir de `benchmark_results.json` — pas inventés
- ✅ Tous les exemples de code doivent fonctionner avec l'API réelle telle qu'implémentée
- ✅ Les noms d'endpoints doivent correspondre exactement aux routes du projet
- ✅ Les codes d'erreur doivent être extraits du vrai code, pas inventés
- ❌ Pas de features non implémentées présentées comme disponibles
- ❌ Pas de "coming soon" sauf pour multivariate et ensemble (les seuls stubs réels)
- ❌ Pas de chiffres de performance inventés

---

## ORDRE D'EXÉCUTION

1. Lis `benchmark_results.json` et note les vrais chiffres MAE/RMSE/MAPE/sMAPE
2. Lis `app/middleware/error_handler.py` et liste tous les codes d'erreur
3. Lis `app/config.py` et `app/services/credits.py` pour les vrais noms de plans
4. Lis `docs/examples/python_example.py` pour les exemples de code
5. Produis `pricing_analysis.md` en premier — attends validation mentale avant de continuer
6. Génère les 8 autres fichiers dans l'ordre
7. Vérifie que tous les liens, noms d'endpoints et chiffres sont cohérents
8. Commit : `git add docs/rapidapi/final/ && git commit -m "docs: RapidAPI publication content"`

---

## VALIDATION

À la fin, génère `docs/rapidapi/final/SUMMARY.md` qui liste :
- Les 9 fichiers générés avec leur chemin
- Le nombre de mots de chaque fichier
- Les 3 points de vigilance (endroits où tu as dû faire des choix éditoriaux)
- Les placeholders à remplacer manuellement (URL RapidAPI, IP VPS, etc.)
