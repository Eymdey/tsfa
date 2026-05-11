# TSFA RapidAPI Publication — Generation Summary

Generated: 2026-05-11

---

## Generated Files

| # | File | Words | Notes |
|---|---|---|---|
| 0 | `pricing_analysis.md` | 710 | Pricing vs code analysis — read this first |
| 1 | `short_description.txt` | 16 | RapidAPI listing tagline (93 chars) |
| 2 | `long_description.md` | 548 | Endpoints tab description |
| 3 | `readme.md` | 1,240 | Hub "About" README |
| 4 | `tutorial_01_quickstart.md` | 511 | First forecast in 5 minutes |
| 5 | `tutorial_02_batch_forecasting.md` | 434 | Batch endpoint tutorial |
| 6 | `tutorial_03_backtesting.md` | 446 | /validate backtesting tutorial |
| 7 | `spotlights.md` | 100 | 3 RapidAPI spotlight entries |
| 8 | `website_landing_page.html` | 1,680 | Full landing page (HTML+CSS, zero deps) |
| 9 | `caddyfile_update.md` | 390 | Caddy config + DNS + systemd instructions |

**Total:** 6,075 words across 10 files.

---

## Three Editorial Choices

### 1. Model latency figures are estimates, not measured benchmarks

The benchmark results (`benchmark_results.json`) contain only accuracy metrics (MAE, RMSE, MAPE, sMAPE).
No per-call latency was measured. The latency ranges in the Models tables (`<300ms` for ARIMA, `1-4s`
for Chronos) are estimates based on what's documented in the code (local CPU vs Modal GPU) and are
plausible for these model sizes.

**Action:** Run an explicit latency benchmark (e.g., using `time.perf_counter` around `run_univariate_forecast`)
and update these figures before publishing.

### 2. BASIC plan advertised as "500 credits/month" rather than "100 requests/month"

The proposed pricing says "100 requests/month" for BASIC but `app/config.py` grants `plan_free_credits = 500`.
I chose 500 to keep the docs consistent with the actual code behavior. See `pricing_analysis.md` section 2.2
for the full analysis. **This requires a decision from you before publishing.**

### 3. Chronos/LSTM benchmarks are noted as "ARIMA-fallback" results

The benchmark runner was executed with `--local-only` flag, which means Chronos and LSTM results
in the JSON are actually ARIMA fallback results. I documented this transparently in `readme.md`
("Full GPU benchmark results will be added in a future update") rather than presenting ARIMA numbers
as Chronos/LSTM performance.

---

## Placeholders to Replace Manually

| Placeholder | Location | What to replace with |
|---|---|---|
| `https://rapidapi.com/dorianmrt/api/tsfa` | `website_landing_page.html` (4×), tutorials | Real RapidAPI listing URL once published |
| `https://tsfa.p.rapidapi.com` | All files | Real RapidAPI proxy URL (assigned after submission) |
| `IP_DU_VPS` | `caddyfile_update.md` | Your Hetzner VPS IPv4 address |
| `contact@eymdey-network.com` | `website_landing_page.html` footer | Your actual contact email |
| `https://github.com/dorianmrt/tsfa` | `readme.md`, `website_landing_page.html` | Real GitHub repo URL |
| `YOUR_RAPIDAPI_KEY` | All code examples | Left as placeholder intentionally |

---

## Next Steps

1. Resolve the BASIC plan credit count (100 vs 500) — update either the code or the docs
2. Measure real per-call latency for ARIMA and Chronos and update the Models tables
3. Run GPU benchmarks for Chronos/LSTM once Modal is fully configured, update benchmark tables
4. Replace all placeholders above once the RapidAPI submission is approved
5. Commit: `git add docs/rapidapi/final/ && git commit -m "docs: RapidAPI publication content"`
