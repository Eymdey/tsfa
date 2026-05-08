# project-context.md
> Contexte stratégique — Projet API B2D Solo
> Auteur : Dorian Marty | Mis à jour : Mai 2026

---

## 1. Point de départ — Le problème du freelance classique

Dorian Marty, AI/ML Engineer (3 ans d'expérience, Thales LAS, EPSI MSc Expert IA), a tenté d'accéder au marché freelance via Malt et Upwork. Résultat après 2 semaines : zéro mission.

**Diagnostic :**
- **Malt** : algorithme qui favorise les profils déjà notés → cercle vicieux pour les nouveaux entrants.
- **Upwork** : système de "connects" payants, concurrence massive, ROI du temps passé à postuler trop faible.
- **Problème structurel** : le modèle freelance = vendre du temps contre de l'argent. Plafonné. Dépendant d'une visibilité permanente.

**Décision** : abandonner le modèle freelance classique et construire un **actif qui génère des revenus sans que Dorian soit le produit**.

---

## 2. Modèle choisi — API / SaaS technique B2D (Business-to-Developer)

### Pourquoi ce modèle
- Vente à des développeurs et équipes tech, pas à des utilisateurs finaux.
- Distribution via marketplaces (RapidAPI, AWS Marketplace, HuggingFace Hub) → **pas besoin de personal brand ni de marketing personnel**.
- Le produit se vend par sa documentation, ses benchmarks publics, et ses performances mesurables.
- Revenus décorrélés du temps passé une fois le produit lancé.

### Ce que ce modèle n'est pas
- Pas de vente directe B2B (cycle long, relation client, visibilité requise).
- Pas de SaaS vertical grand public (marketing, acquisition, support lourd).
- Pas d'info-produit ou de personal brand.

---

## 3. Analyse des marketplaces — Chiffres réels

| Marketplace | Commission | Tu gardes | Audience | Barrière d'entrée |
|---|---|---|---|---|
| **RapidAPI / Rapid Hub** | 25% flat | 75% | 4M+ devs | Très faible |
| **AWS Marketplace (SaaS)** | 3% | 97% | Enterprise | Modérée |
| **AWS Marketplace (AMI/ML)** | 20% | 80% | Teams cloud | Modérée |
| **Azure Marketplace** | 3% | 97% | Enterprise | Modérée |
| **Google Cloud Marketplace** | 3% (1.5% renouvellement) | 97% | Teams GCP | Modérée |
| **HuggingFace Hub** | 0% (pas de marketplace revente) | 100% | 5M+ devs ML | Très faible |

**Marché global AI API :** $33B en 2024 → $179B en 2030 (CAGR 32.2% — source MarketsandMarkets).

**Stratégie marketplace :**
1. **Phase 1 — Validation** : RapidAPI (trafic organique immédiat, friction zéro, freemium natif).
2. **Phase 2 — Scale** : Migration AWS Marketplace SaaS (97% de marge, accès budgets cloud enterprise pré-provisionnés).
3. **HuggingFace** : Canal de crédibilité technique, pas de revenu direct. Publication de modèles open weights + benchmarks = trafic entrant qualifié.

---

## 4. Les 6 niches identifiées

### 🥇 Niche 1 — Time Series Forecasting API *(recommandée en priorité)*
**Gap marché :** Pas d'API combinant zero-shot forecasting multivarié + intervalles de confiance + endpoint REST propre. Les devs assemblent tout manuellement.
**Stack :** Chronos/Moirai (open weights, fine-tunable) + FastAPI + GPU inference on-demand.
**Public :** Startups logistics, fintech, energy, e-commerce.
**Pricing type :** Free / $49 / $199 / $499 par mois.

### 🥈 Niche 2 — Document Intelligence API (extraction structurée)
**Gap marché :** AWS Textract/Azure Document Intelligence très mauvais sur documents français (CERFA, factures FR, FEC). Prix : $1.50-$15/1000 pages. Opportunité de se positionner à $0.30-0.80/page avec meilleure pertinence FR/EU.
**Stack :** LayoutLMv3 ou Donut (fine-tuné) + post-processing LLM + FastAPI.
**Public :** Comptables, cabinets, startups fintech EU.
**Churn le plus bas de toutes les niches** (intégration profonde dans les pipelines).

### 🥉 Niche 3 — Anomaly Detection API *(terrain natif de Dorian)*
**Gap marché :** APIs existantes = wrappers Isolation Forest basiques, pas de multivarié, pas d'explainability. Dorian a construit DASY chez Thales — expertise directement transposable.
**Stack :** Isolation Forest + LSTM/GRU + LOF + FastAPI.
**Public :** Startups DevOps/SRE, fintech, IoT.
**Avantage :** Crédibilité réelle terrain critique (Thales ATC).

### ⚡ Niche 4 — ML Feature Engineering & Data Quality API
**Gap marché :** Featuretools et tsfresh = librairies locales Python, aucune API REST propre. Besoin universel (60-80% du temps data = preprocessing).
**Stack :** Pandas + tsfresh + custom ML + FastAPI.
**Public :** Data engineers, ML teams.

### 🎯 Niche 5 — Causal Inference & Statistical Testing API
**Gap marché :** Choix du bon test statistique (Mann-Whitney vs t-test, CUSUM, DiD) souvent fait au hasard. Pas d'API "statistical advisor" sur le marché.
**Stack :** SciPy + Statsmodels + LLM pour interprétation + FastAPI.
**Public :** Data analysts, product managers, équipes expérimentation.

### 🔮 Niche 6 — LLM Structured Extraction API
**Gap marché :** Extraction text → JSON structuré avec validation de schéma, retry auto, confidence score. Meilleur que les appels LLM directs bruts.
**Stack :** LLM (Claude/Mistral) + Pydantic validation + FastAPI.
**Public :** Dev teams qui construisent des pipelines AI.

---

## 5. Recommandation de priorité

| Phase | Action | Timeline |
|---|---|---|
| **Phase 1** | Lancer Niche 1 (Time Series Forecasting) sur RapidAPI | Semaines 1-6 |
| **Phase 1b** | Publier modèle open weights + benchmark sur HuggingFace | Semaine 4-6 |
| **Phase 2** | Migration AWS Marketplace SaaS | Mois 3-4 |
| **Phase 3** | Lancer Niche 2 ou 3 en parallèle | Mois 6-9 |

**Pourquoi Time Series Forecasting en priorité :**
- Marché le plus large (logistics, finance, energy, e-commerce = universels).
- Concurrents identifiables (Nixtla, quelques startups US) → différentiation possible par domaine EU ou prix.
- Stack moins complexe que Document Intelligence (pas de fine-tuning vision).
- Modèles fondation open source disponibles (Chronos, Moirai, TimesFM).

---

## 6. Scenarios de revenus réalistes

| Scenario | Timeline | Clients | Revenue mensuel net (après marketplace) |
|---|---|---|---|
| **Conservateur** | 12 mois | 15-20 clients | 3 000 – 6 000 €/mois |
| **Réaliste** | 18 mois | 50-80 clients | 12 000 – 20 000 €/mois |
| **Optimiste** | 24 mois | 150+ clients (2 APIs) | 35 000 – 60 000 €/mois |

---

## 7. Stack technique cible (global)

```
Inférence ML     → Modal.com ou Replicate (GPU on-demand, coût fixe ~0 au départ)
API Layer        → FastAPI (Python) — performant, typage Pydantic, docs auto OpenAPI
Auth & Billing   → RapidAPI (Phase 1) → Stripe + API Gateway custom (Phase 2)
Hosting API      → Hetzner VPS (1 vCPU, 2GB RAM) pour le routing + FastAPI
Docs             → Mintlify ou Readme.io
CI/CD            → GitHub Actions → Docker → déploiement auto
Monitoring       → Grafana + Prometheus (Dorian connaît déjà Grafana)
MLflow           → Tracking des expériences et versions de modèles
```

---

## 8. Principes non-négociables du projet

1. **Zero personal brand requis** — le produit se vend par ses benchmarks et sa documentation.
2. **Infrastructure as code** — tout dockerisé, reproductible, scalable.
3. **Open weights en vitrine** — publier les modèles sur HuggingFace crée de la crédibilité sans effort marketing.
4. **Pay-as-you-grow** — coûts d'infrastructure quasi nuls au départ (Modal/Replicate = 0€ sans trafic).
5. **Multi-marketplace dès la V2** — ne pas être dépendant d'un seul canal de distribution.
