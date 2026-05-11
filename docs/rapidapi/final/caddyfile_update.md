# Caddy Configuration — TSFA Production Setup

---

## DNS Records (OVH)

Add these two A records in the OVH DNS zone for `eymdey-network.com`:

```
Type A | Name : api  | Value : IP_DU_VPS | TTL : 300
Type A | Name : tsfa | Value : IP_DU_VPS | TTL : 300
```

Replace `IP_DU_VPS` with your Hetzner VPS IPv4 address.
Propagation: 5–30 minutes with TTL=300.

---

## Caddyfile

Place this in `/etc/caddy/Caddyfile` on the Hetzner VPS:

```caddy
# TSFA API — proxy to FastAPI (Uvicorn on port 8000)
api.eymdey-network.com {
    reverse_proxy localhost:8000 {
        header_up X-Forwarded-For {remote_host}
        header_up X-Real-IP {remote_host}
    }

    # Security headers
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        -Server
    }

    log {
        output file /var/log/caddy/api.log {
            roll_size 10mb
            roll_keep 5
        }
    }
}

# TSFA Landing Page — static HTML file
tsfa.eymdey-network.com {
    root * /var/www/tsfa
    file_server

    # Security headers
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
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

---

## Deployment Steps

### 1. Deploy the landing page

```bash
# Create the web root
sudo mkdir -p /var/www/tsfa

# Copy the landing page
sudo cp docs/rapidapi/final/website_landing_page.html /var/www/tsfa/index.html
sudo chown -R caddy:caddy /var/www/tsfa
```

### 2. Validate and reload Caddy

```bash
# Validate config syntax before reloading
caddy validate --config /etc/caddy/Caddyfile

# Reload without downtime
sudo systemctl reload caddy
```

### 3. Verify TLS certificates

Caddy automatically provisions Let's Encrypt certificates for both subdomains.
Check status after DNS propagation:

```bash
curl -I https://api.eymdey-network.com/v1/models
curl -I https://tsfa.eymdey-network.com/
```

Both should return `HTTP/2 200` with `Strict-Transport-Security` header present.

---

## FastAPI Startup

Ensure the TSFA API runs as a systemd service on port 8000:

```bash
# /etc/systemd/system/tsfa.service
[Unit]
Description=TSFA FastAPI service
After=network.target redis.service

[Service]
User=dorian
WorkingDirectory=/home/dorian/tsfa
EnvironmentFile=/home/dorian/tsfa/.env
ExecStart=/home/dorian/tsfa/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable tsfa
sudo systemctl start tsfa
```

---

## Notes

- Caddy listens on 443 (HTTPS) and 80 (HTTP → redirect). No manual cert management needed.
- FastAPI is bound to `127.0.0.1:8000` (not `0.0.0.0`) — not directly accessible from outside.
- RapidAPI routes requests through its gateway → `api.eymdey-network.com` → Caddy → FastAPI.
- Set `ENVIRONMENT=production` and `RAPIDAPI_PROXY_SECRET=<your-secret>` in `.env` to enforce
  the RapidAPI proxy check (rejects direct API calls that bypass the gateway).
