# TSFA Pricing

## Plans

### Free — $0/month
- **100 credits/month**
- 10 requests/minute
- Univariate forecasting (`/v1/forecast/univariate`)
- Backtesting (`/v1/validate`)
- No batch forecasting
- Community support

### Basic — $9/month
- **1,000 credits/month**
- 30 requests/minute
- Univariate forecasting
- Backtesting
- No batch forecasting
- Email support

### Pro — $29/month
- **10,000 credits/month**
- 100 requests/minute
- Univariate forecasting
- Backtesting
- **Batch forecasting** (up to 50 series/request)
- Priority email support
- SLA: 99.5% uptime

### Ultra — $99/month
- **100,000 credits/month**
- 500 requests/minute
- Univariate forecasting
- Backtesting
- **Batch forecasting** (up to 500 series/request)
- Dedicated support channel
- SLA: 99.9% uptime

---

## Credit Costs per Model

| Model | Credits per Request |
|-------|-------------------|
| `auto` (AutoARIMA) | 1 |
| `arima` | 1 |
| `chronos` | 1 |
| `lstm` | 2 |
| `tide` *(Phase 2)* | 3 |
| `ensemble` *(Phase 2)* | 5 |

---

## Credit Top-ups

Need more credits within the month? Contact support for a one-time credit top-up at **$0.001 per credit** (minimum 1,000 credits).

---

## Overage Policy

Requests that exceed your monthly quota will receive a `402 Payment Required` response. Upgrade your plan or wait for the monthly reset on the 1st.

---

## Billing

- Billed monthly, auto-renewed
- Credits reset on the 1st of each month (unused credits do not roll over)
- Cancel anytime — access continues until end of the billing period
- All prices in USD
