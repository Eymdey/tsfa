# Pricing Analysis — TSFA RapidAPI Publication

Generated: 2026-05-11

---

## 1. Proposed Pricing vs Original Specs

Original specs (`project-specs.md`) defined **4 tiers**: Free / Basic / Pro / Ultra.  
Proposed pricing also has **4 tiers** but with different names: BASIC / PRO / ULTRA / MEGA.

| Proposed Name | Price | Requests/month | Original Equivalent | Original Name |
|---|---|---|---|---|
| BASIC | $0.00 | 100 | Free tier | free |
| PRO | $49.00 | 10,000 | Basic tier | basic |
| ULTRA | $199.00 | 50,000 | Pro tier | pro |
| MEGA | $499.00 | 200,000 | Ultra tier | ultra |

**Conclusion:** the 4-tier structure is preserved. The names shift up (Basic→free, Pro→basic, etc.).  
This is a naming convention change, not a structural change.

---

## 2. Incohérences avec le code

### 2.1 Noms de plans — BREAKING CHANGE

The code (`app/dependencies.py`, `app/services/credits.py`) uses these valid plan names:
```python
VALID_PLANS: set[str] = {"free", "basic", "pro", "ultra"}
```

RapidAPI sends the plan name via the `X-RapidAPI-Subscription` header. If the RapidAPI plans are
named `BASIC`, `PRO`, `ULTRA`, `MEGA`, the header values forwarded will be those strings (lowercased
by the gateway: `basic`, `pro`, `ultra`, `mega`). The plan `mega` is **not in `VALID_PLANS`** and
`basic` maps to the wrong tier.

**Impact:** Without a code update, all MEGA subscribers would fall back to the `free` plan.

### 2.2 Credit Limits — One discrepancy

| Code Plan | Code Credits/month | Proposed Plan | Proposed Requests/month | Match? |
|---|---|---|---|---|
| free | 500 | BASIC | 100 | **NO — 500 ≠ 100** |
| basic | 10,000 | PRO | 10,000 | YES |
| pro | 50,000 | ULTRA | 50,000 | YES |
| ultra | 200,000 | MEGA | 200,000 | YES |

The BASIC free tier says "100 requests/month" but the code grants 500 credits. For ARIMA (1 credit/call),
that means 500 actual requests, not 100.

**Decision required:** Either set `plan_free_credits = 100` in `config.py`, or advertise "500 requests/month"
for BASIC on the listing. Advertising 100 and granting 500 is fine (underpromise/overdeliver) but
inconsistent. Recommend aligning to 500 in the pricing page.

### 2.3 Rate Limits

Rate limits are defined per code plan:
```
free: 10 req/min | basic: 30 req/min | pro: 100 req/min | ultra: 300 req/min
```
After renaming, these map to:
```
BASIC: 10 req/min | PRO: 30 req/min | ULTRA: 100 req/min | MEGA: 300 req/min
```
These are reasonable and should be displayed on the listing.

### 2.4 Batch Access

Currently, `forecast.py` restricts batch to plans `pro` and `ultra` (code names). After renaming,
this must map to `ULTRA` and `MEGA`. The code must be updated accordingly.

---

## 3. Files to Update if Plan Names Change

If adopting the BASIC/PRO/ULTRA/MEGA naming (recommended path):

| File | Change needed |
|---|---|
| `app/dependencies.py` | `VALID_PLANS = {"basic", "pro", "ultra", "mega"}` |
| `app/config.py` | Rename `plan_free_credits` → `plan_basic_credits`, etc. (and add `plan_mega_credits`) |
| `app/services/credits.py` | Update `PLAN_LIMITS` and `RATE_LIMITS` dict keys |
| `app/routers/forecast.py` | Update batch restriction check: `if plan in ("basic", "pro")` → restrict free-equivalent |

Alternatively, keep the code plan names unchanged and configure RapidAPI plan aliases. RapidAPI
allows custom plan names that map to forwarded header values. You can name the plans
"BASIC/PRO/ULTRA/MEGA" on the listing but configure the subscription header to forward `free/basic/pro/ultra`.
**This is the lower-risk option — no code changes required.**

---

## 4. Recommendation

**Adopt the proposed pricing with minor adjustments:**

1. **Plan names on RapidAPI:** Use BASIC/PRO/ULTRA/MEGA as marketing names. Configure RapidAPI
   to forward `free`/`basic`/`pro`/`ultra` in the `X-RapidAPI-Subscription` header. This avoids
   any code change.

2. **BASIC tier volume:** Advertise **500 requests/month** (aligned with `plan_free_credits = 500`),
   not 100. Alternatively set `plan_free_credits = 100` in `config.py` if 100 is the intended limit.

3. **Pricing itself is coherent** with the market positioning (project-context.md):
   - BASIC free: discovery tier, no revenue expectation
   - PRO $49 for 10K calls: competitive with Nixtla TimeGPT (~$50-100 range)
   - ULTRA $199 for 50K: reasonable for startups and mid-size teams
   - MEGA $499 for 200K: competitive enterprise entry point

4. **Do not rename plans in code** — use RapidAPI header mapping instead.

**Current blocker:** Clarify whether BASIC = 100 or 500 requests/month before publishing.
