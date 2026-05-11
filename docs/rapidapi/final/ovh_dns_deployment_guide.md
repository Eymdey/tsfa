# Guide de déploiement — OVH DNS + Hetzner VPS + Caddy

Domaine : **eymdey-network.com**
Objectif : Servir `api.eymdey-network.com` (FastAPI) et `tsfa.eymdey-network.com` (landing page HTML).

---

## Étape 0 — Récupérer l'IP du VPS Hetzner

Avant tout, tu as besoin de l'IPv4 publique de ton VPS Hetzner.

```bash
# Sur ton VPS via SSH :
curl -4 ifconfig.me
# Ou depuis la console Hetzner Cloud
```

Note cette IP — tu en auras besoin à l'étape 1. Elle ressemble à `49.x.x.x` ou `78.x.x.x`.

---

## Étape 1 — Configurer les enregistrements DNS sur OVH

### 1.1 Connexion

1. Va sur **manager.ovh.com**
2. Connecte-toi avec tes identifiants OVH
3. Dans le menu de gauche : **Web Cloud** → **Noms de domaine**
4. Clique sur **eymdey-network.com**
5. Onglet : **Zone DNS**

### 1.2 Ajouter les enregistrements A

Clique sur **Ajouter une entrée** (bouton en haut à droite de la zone DNS).

#### Enregistrement 1 — API

```
Type   : A
Sous-domaine : api
Cible  : VOTRE_IP_VPS
TTL    : 300 (ou "Personnalisé" → 300)
```

Clique **Suivant** → **Confirmer**.

#### Enregistrement 2 — Landing page

```
Type   : A
Sous-domaine : tsfa
Cible  : VOTRE_IP_VPS
TTL    : 300 (ou "Personnalisé" → 300)
```

Clique **Suivant** → **Confirmer**.

### 1.3 Vérifier la propagation DNS

La propagation prend 1–30 minutes avec TTL=300.

```bash
# Depuis ton terminal local — attends que les deux répondent avec l'IP du VPS :
dig +short api.eymdey-network.com
dig +short tsfa.eymdey-network.com

# Alternative :
nslookup api.eymdey-network.com
nslookup tsfa.eymdey-network.com
```

Les deux doivent retourner l'IP de ton VPS Hetzner avant de continuer.

---

## Étape 2 — Préparer le VPS Hetzner

Connecte-toi en SSH à ton VPS.

### 2.1 Installer Caddy (si pas déjà installé)

```bash
# Ubuntu 24.04
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
  | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
  | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update && sudo apt install caddy -y

# Vérification
caddy version
```

### 2.2 Déployer la landing page

```bash
# Créer le dossier web
sudo mkdir -p /var/www/tsfa

# Copier la landing page depuis le repo
sudo cp ~/tsfa/docs/rapidapi/final/website_landing_page.html /var/www/tsfa/index.html

# Permissions Caddy
sudo chown -R caddy:caddy /var/www/tsfa
sudo chmod -R 755 /var/www/tsfa
```

### 2.3 Créer les dossiers de logs

```bash
sudo mkdir -p /var/log/caddy
sudo chown -R caddy:caddy /var/log/caddy
```

---

## Étape 3 — Configurer Caddy

### 3.1 Écrire le Caddyfile

```bash
sudo nano /etc/caddy/Caddyfile
```

Remplace le contenu existant par :

```caddy
# ── TSFA API — proxy vers FastAPI (port 8000) ──────────────────────
api.eymdey-network.com {
    reverse_proxy localhost:8000 {
        header_up X-Forwarded-For {remote_host}
        header_up X-Real-IP {remote_host}
        header_up Host {host}
    }

    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        Referrer-Policy "strict-origin-when-cross-origin"
        -Server
    }

    log {
        output file /var/log/caddy/api.log {
            roll_size 10mb
            roll_keep 5
        }
    }
}

# ── TSFA Landing Page — fichier HTML statique ──────────────────────
tsfa.eymdey-network.com {
    root * /var/www/tsfa
    file_server

    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "SAMEORIGIN"
        Cache-Control "public, max-age=3600"
        -Server
    }

    log {
        output file /var/log/caddy/tsfa.log {
            roll_size 10mb
            roll_keep 5
        }
    }
}
```

### 3.2 Valider et recharger

```bash
# Valider la syntaxe AVANT de recharger (évite les coupures)
caddy validate --config /etc/caddy/Caddyfile

# Si "Valid configuration" → recharger
sudo systemctl reload caddy

# Vérifier le statut
sudo systemctl status caddy
```

Caddy provisionne automatiquement les certificats Let's Encrypt pour les deux sous-domaines.
Aucune configuration SSL manuelle nécessaire.

---

## Étape 4 — Démarrer l'API FastAPI

### 4.1 Créer le service systemd

```bash
sudo nano /etc/systemd/system/tsfa.service
```

```ini
[Unit]
Description=TSFA — Time Series Forecasting API
After=network.target redis.service
Wants=redis.service

[Service]
User=dorian
Group=dorian
WorkingDirectory=/home/dorian/tsfa
EnvironmentFile=/home/dorian/tsfa/.env
ExecStart=/home/dorian/tsfa/.venv/bin/uvicorn app.main:app \
    --host 127.0.0.1 \
    --port 8000 \
    --workers 2 \
    --access-log \
    --log-level info
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable tsfa
sudo systemctl start tsfa
sudo systemctl status tsfa
```

### 4.2 Vérifier que l'API répond en local

```bash
curl http://localhost:8000/v1/models
# Doit retourner JSON avec la liste des modèles
```

---

## Étape 5 — Variables d'environnement (.env)

Assure-toi que `/home/dorian/tsfa/.env` contient :

```env
ENVIRONMENT=production
RAPIDAPI_PROXY_SECRET=<copié depuis le dashboard RapidAPI → API Settings → Proxy Secret>
SECRET_KEY=<chaîne aléatoire longue — utilise: openssl rand -hex 32>
REDIS_URL=redis://localhost:6379/0
USE_MODAL=true
MODAL_TOKEN_ID=<ton token Modal>
MODAL_TOKEN_SECRET=<ton secret Modal>
```

> **Important :** En `ENVIRONMENT=production`, l'API vérifie le header `X-RapidAPI-Proxy-Secret`
> sur chaque requête. Si ce header est absent ou incorrect, la requête retourne HTTP 403.
> C'est la protection qui empêche les appels directs sans passer par RapidAPI (bypass du billing).

---

## Étape 6 — Vérifications finales

```bash
# 1. HTTPS sur l'API
curl -I https://api.eymdey-network.com/v1/models
# Attendu : HTTP/2 200 + Strict-Transport-Security header

# 2. HTTPS sur la landing page
curl -I https://tsfa.eymdey-network.com/
# Attendu : HTTP/2 200 + Content-Type: text/html

# 3. Redirection HTTP → HTTPS automatique (Caddy le fait nativement)
curl -I http://api.eymdey-network.com/v1/models
# Attendu : HTTP/1.1 301 Moved Permanently → https://...

# 4. Test d'un vrai appel API
curl -X POST https://api.eymdey-network.com/v1/forecast/univariate \
  -H "Content-Type: application/json" \
  -H "X-Plan: free" \
  -d '{"series":[1,2,3,4,5,6,7,8,9,10,11,12],"horizon":3,"frequency":"D","model":"arima"}'
# En dev mode (ENVIRONMENT=development) : retourne un forecast
# En prod mode : retourne 403 FORBIDDEN (car pas de X-RapidAPI-Proxy-Secret)
```

---

## Récapitulatif des URLs

| URL | Pointe vers | Description |
|---|---|---|
| `https://tsfa.eymdey-network.com` | `/var/www/tsfa/index.html` | Landing page publique |
| `https://api.eymdey-network.com/v1/...` | `localhost:8000` (FastAPI) | API — accès via RapidAPI uniquement en prod |

---

## Troubleshooting

**Caddy ne démarre pas après `reload` :**
```bash
sudo journalctl -u caddy -n 50 --no-pager
```
Vérifie que le DNS pointe bien vers le VPS — Let's Encrypt doit pouvoir résoudre le domaine pour émettre le certificat.

**L'API retourne 502 Bad Gateway :**
```bash
sudo systemctl status tsfa
sudo journalctl -u tsfa -n 30 --no-pager
# FastAPI n'est probablement pas démarré sur le port 8000
```

**Redis indisponible (crédits non trackés) :**
```bash
sudo systemctl status redis
sudo systemctl start redis
```
Sans Redis, l'API fonctionne mais le rate limiting et le crédit tracking sont désactivés (no-op).

**Certificat SSL non provisionné :**
Attends 5–10 minutes après la propagation DNS. Caddy contacte Let's Encrypt automatiquement.
Vérifie avec : `sudo journalctl -u caddy | grep acme`
