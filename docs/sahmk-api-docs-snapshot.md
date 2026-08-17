# SAHMK API Documentation

> Machine-readable API documentation for developers and AI agents.
> Base URL: `https://api.sahmk.sa/api/v1`
> Portal: https://sahmk.sa/developers
>
> Existing integrations using `app.sahmk.sa` will continue to work.
>
> Example source policy: GET response examples are captured from live API calls. POST and WebSocket payload examples are protocol references and are not live-sampled in docs to avoid write side effects and session dependencies.

## Recommended Flow

- Start here: make your first REST request with `GET /quote/{symbol}/`
- Build faster: use the official Python SDK or CLI
- Add AI workflows: connect the MCP server or read this file directly
- Scale up: move to WebSocket and Realtime Event Engine rules when polling is not enough

---

## Start Here

Create an account, get your API key from the dashboard, and make your first request:

```bash
curl "https://api.sahmk.sa/api/v1/quote/2222/" \
  -H "X-API-Key: YOUR_API_KEY"
```

Expected response:

```json
{
  "symbol": "2222",
  "name_en": "Saudi Arabian Oil Co",
  "price": 26.6,
  "change_percent": 0.0,
  "volume": 6601208,
  "updated_at": "2026-08-12T12:20:00+00:00",
  "is_delayed": false
}
```

You just fetched Saudi market data from SAHMK. Free and Starter return delayed data by default;
Pro and higher plans can return real-time data.

Use exchange symbols in the path (for example `2222`).
If you need name/alias resolution, pass `identifier` as a query param:
`GET /quote/{symbol}/?identifier=أرامكو`.

---

## SDK & Tools

```bash
pip install -U sahmk
export SAHMK_API_KEY="your_api_key"
sahmk quote "Saudi Aramco"
```

Upgrade note: if a newly documented SDK/CLI feature is missing locally, run `pip install -U sahmk` to get the latest commands and interval support.

Python SDK:

```python
from sahmk import SahmkClient

client = SahmkClient(api_key="YOUR_API_KEY")

# Discover symbols before quote/company calls
directory = client.companies(search="aramco", market="NOMUC", limit=20, offset=0)
symbol = directory["results"][0]["symbol"]

print(client.quote("أرامكو السعودية"))
print(client.company(symbol))
```

Full examples: https://github.com/sahmk-sa/sahmk-python
PyPI: https://pypi.org/project/sahmk/

---

## AI & Agents

Use SAHMK inside Claude Desktop, Cursor, and other MCP-compatible clients.

```bash
pip install -U sahmk-mcp
```

Upgrade note: if MCP tools reject newer params (for example newer historical intervals), run `pip install -U sahmk-mcp` and restart your MCP client.

Configuration (Claude Desktop and Cursor):

```json
{
  "mcpServers": {
    "sahmk": {
      "command": "sahmk-mcp",
      "env": {
        "SAHMK_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

Available MCP tools:
- `get_quote` — Price, change, volume, and liquidity for one company (delayed on Free/Starter; real-time on Pro+)
- `get_quotes` — Batch quotes for multiple companies (up to 50)
- `get_market_summary` — Market summary by `index` (default `TASI`) with index level, breadth, mood, and `is_delayed`
- `companies_list` — Company directory lookup for symbol discovery with `search`, `market`, `limit`, and `offset`
- `get_company` — Company profile, sector, fundamentals
- `get_historical` — Historical OHLCV data (`1d`, `1w`, `1m`, `30m`, `60m`; plan/date-window limits apply)

Source: https://github.com/sahmk-sa/sahmk-mcp
PyPI: https://pypi.org/project/sahmk-mcp/
Tutorial: https://sahmk.sa/developers/tutorials/sahmk-mcp-ai-agents

---

## Authentication

All requests require the `X-API-Key` header:

```
X-API-Key: YOUR_API_KEY
```

API key formats:
- `shmk_live_*` — Production keys
- `shmk_test_*` — Test keys (same data access; usage counts toward the account's shared daily quota)

---

## Subscription Plans

| Feature | Free | Starter (149 SAR/mo) | Pro (499 SAR/mo) | Business | Enterprise (Custom) |
|---------|------|----------------------|------------------|----------|---------------------|
| Requests/day | 100 | 5,000 | 50,000 | 150,000 | Custom |
| Requests/min | 10 | 100 | 500 | 1,000 | Custom |
| API Keys | 1 | 3 | 10 | 30 | Custom |
| Real-time data | No (15-min delay) | No (15-min delay) | Yes | Yes | Yes |
| Historical data | No | Yes | Yes | Yes | Yes |
| Financials | No | Yes | Yes | Yes | Yes |
| Dividends | No | Yes | Yes | Yes | Yes |
| Bulk quotes (/quotes/) | No | Yes | Yes | Yes | Yes |
| Live trades (REST + WS) | No | No | Yes | Yes | Yes |
| Company fundamentals | Basic | Full | Full | Full | Full |
| Technical indicators | No | No | Yes | Yes | Yes |
| Fair price (proprietary) | No | No | Yes | Yes | Yes |
| Stock events | No | No | Yes | Yes | Yes |
| Event webhooks | 0 | 0 | 3 | 10 | Custom |
| Event rules | 0 | 0 | 10 | 50 | Custom |

*Prices exclude 15% VAT*

**Enterprise (Custom):** Limits designed for your workload + dedicated infra. Limits are finalized after a quick usage review (symbols, traffic, concurrency).

**Enterprise options:**
- **Option A — Shared high-volume:** higher daily quota + higher burst + prioritized processing + custom limits for webhooks/alerts.
- **Option B — Dedicated:** dedicated VM / dedicated cache (optional) + cloud Postgres + SLA; scalable solutions for your use case.

---

## Endpoints

### Path vs Query Parameters

- Use path parameters for single-resource endpoints (example: `GET /quote/{symbol}/`).
- Use query parameters to filter collection endpoints (example: `GET /events/?symbol=2222&limit=20`).
- Error handling convention: common HTTP/API errors are centralized in [`Error Codes`](#error-codes). Endpoint sections only show endpoint-specific errors when needed.

### Stocks

#### GET /quote/{symbol}/
Get current price for a single stock.

**Plan:** Free

**Parameters:**
- `symbol` (path, required): Exchange symbol (example: `2222`)
- `identifier` (query, optional): Arabic/English name or alias for resolution (example: `أرامكو`)
- `data_mode` (query, optional): `delayed` or `realtime`; realtime requires Pro+

**Example with identifier resolution:** `GET /quote/2222/?identifier=أرامكو`

> **Need valid symbols first?** Use `GET /companies/` to discover symbols by symbol, Arabic name, or English name before calling quote endpoints.

If `identifier` matches multiple companies, the API returns HTTP 409 with
`error.code: "AMBIGUOUS_IDENTIFIER"` and a `candidates` array.

**Response:**
```json
{
  "symbol": "2222",
  "name": "أرامكو السعودية",
  "name_en": "Saudi Arabian Oil Co",
  "price": 26.6,
  "change": 0.0,
  "change_percent": 0.0,
  "open": 26.6,
  "high": 26.68,
  "low": 26.52,
  "previous_close": 26.6,
  "volume": 6601208,
  "value": 175637052.96,
  "bid": 26.6,
  "bid_size": 9181,
  "ask": 26.62,
  "ask_size": 38155,
  "liquidity": {
    "inflow_value": 99498351.21,
    "inflow_volume": 3739041,
    "inflow_trades": 4858,
    "outflow_value": 76138701.51,
    "outflow_volume": 2862167,
    "outflow_trades": 3472,
    "net_value": 23359649.699999988
  },
  "updated_at": "2026-08-12T12:20:00+00:00",
  "is_delayed": false,
  "resolved_instrument": {
    "input": "أرامكو",
    "symbol": "2222",
    "name": "أرامكو",
    "match_type": "alias_exact",
    "confidence": "high"
  }
}
```

If the symbol exists but its current price row is unavailable, the endpoint returns:

```json
{
  "error": {
    "code": "PRICE_DATA_TEMPORARILY_UNAVAILABLE",
    "message": "Price data for '2222' is temporarily unavailable. Please retry shortly."
  }
}
```

This response uses HTTP 409 Conflict.

---

#### GET /quotes/
Get quotes for multiple stocks.

**Plan:** Starter+

Free tier fallback: use `GET /quote/{symbol}/` for single-company quotes.

**Parameters:**
- `symbols` (query, optional): Comma-separated exchange symbols (max 50)
- `identifiers` (query, optional): Comma-separated Arabic/English names or aliases
- `data_mode` (query, optional): `delayed` or `realtime`; realtime requires Pro+

Use exactly one of `symbols` or `identifiers` per request.

- Missing both parameters returns `400 MISSING_PARAM`.
- Providing both returns `400 INVALID_PARAM`.

**Examples:** `/quotes/?symbols=2222,1120,2010` or `/quotes/?identifiers=Aramco,الراجحي`

> **Need valid symbols first?** Use `GET /companies/` to search and validate symbols before batch quote requests.

**Response:**
```json
{
  "quotes": [
    {
      "symbol": "2222",
      "name": "شركة الزيت العربية السعودية",
      "name_en": "Saudi Arabian Oil Co",
      "price": 26.6,
      "change": 0.0,
      "change_percent": 0.0,
      "high": 26.68,
      "low": 26.52,
      "bid": 26.6,
      "ask": 26.62,
      "bid_size": 9181,
      "ask_size": 38155,
      "volume": 6601208,
      "net_liquidity": 23359649.699999988,
      "updated_at": "2026-08-12T13:00:00+00:00",
      "is_delayed": false
    },
    {
      "symbol": "1120",
      "name": "مصرف الراجحي",
      "name_en": "Al Rajhi Banking & Investment Corp SJSC",
      "price": 64.05,
      "change": -0.05,
      "change_percent": -0.08,
      "high": 64.3,
      "low": 63.7,
      "bid": 63.95,
      "ask": 64.05,
      "bid_size": 15,
      "ask_size": 43300,
      "volume": 3775688,
      "net_liquidity": -47806410.94999999,
      "updated_at": "2026-08-12T13:00:00+00:00",
      "is_delayed": false
    }
  ],
  "count": 2,
  "max_symbols": 50,
  "requested_count": 2
}
```

Requests are limited to 50 symbols. If more are requested, the response also includes `truncated: true` and a `warning`; only the first 50 are processed.

With `symbols=`, unknown or internal symbols are omitted rather than returned as per-symbol errors.
Compare `requested_count` with `count` to detect omissions. Use `identifiers=` when explicit
`resolution.not_found` metadata is required.

When `identifiers` is used, the response also includes resolution metadata:

```json
{
  "resolution": {
    "requested_count": 2,
    "resolved_count": 1,
    "ambiguous": [],
    "not_found": [{ "input": "BadName" }]
  }
}
```

---

### Trades

#### GET /market/trades/{symbol}/
Get recent trades for a symbol (newest first).

**Plan:** Pro+

**Parameters:**
- `symbol` (path, required): Exchange symbol (example: `2222`)
- `limit` (query, optional): Max trades returned, newest first (default: `50`, max: `200`). Non-integer values return `400 INVALID_LIMIT`; integer values outside the range are clamped to `1..200`.

**Example:** `GET /market/trades/2222/?limit=1`

**Response:**
```json
{
  "symbol": "2222",
  "updated_at": "2026-08-12T12:19:10+00:00",
  "count": 1,
  "events": [
    {
      "event_time": "2026-08-12T12:19:10+00:00",
      "price": 26.6,
      "quantity": 20,
      "value": 532.0
    }
  ],
  "summary": {
    "event_count": 1,
    "trade_quantity": 20,
    "trade_value": 532.0,
    "latest_event_time": "2026-08-12T12:19:10+00:00"
  }
}
```

**Endpoint-specific errors:**
```json
{
  "error": {
    "code": "INVALID_SYMBOL",
    "message": "Stock symbol '9999' not found."
  }
}

{
  "error": {
    "code": "INVALID_LIMIT",
    "message": "limit must be a valid integer."
  }
}
```

---

### Depth

#### GET /market/depth/{symbol}/
Get an order-book depth snapshot for a symbol.

**Plan:** Pro+ with approved REST depth access

Plan eligibility alone does not activate this market-data entitlement. Returned depth may be lower than requested based on entitlement and market-data availability.

**Parameters:**
- `symbol` (path, required): Exchange symbol (example: `2222`)
- `levels` (query, optional): Requested depth (default: `5`, max: `20`)

Non-integer `levels` falls back to `5`. Common failures include entitlement/access `403` responses
(`PLAN_NOT_ELIGIBLE`, `MARKET_DATA_ENTITLEMENT_REQUIRED`, `MARKET_DATA_TERMS_ACCEPTANCE_REQUIRED`,
or `MARKET_DATA_ENTITLEMENT_SUSPENDED`) and `404 DEPTH_NOT_AVAILABLE` when no usable book exists.

**Response:**
```json
{
  "symbol": "2222",
  "updated_at": "2026-08-12T12:19:54.982770+00:00",
  "session": "atc",
  "book_state": "normal",
  "levels": 5,
  "best_bid": 26.6,
  "best_ask": 26.62,
  "spread": 0.02,
  "spread_bps": 7.52,
  "total_bid_quantity_top5": 241514,
  "total_ask_quantity_top5": 491802,
  "total_bid_quantity": 241514,
  "total_ask_quantity": 491802,
  "level_imbalance": -0.3413,
  "level_imbalance_top5": -0.3413,
  "bids": [
    { "level": 0, "price": 26.6, "quantity": 9181, "order_count": 18 }
  ],
  "asks": [
    { "level": 0, "price": 26.62, "quantity": 38155, "order_count": 17 }
  ],
  "entitled_levels": 5
}
```

---

### Market

#### GET /market/summary/?index=TASI
Get market index and market overview.

**Plan:** Free

**Parameters:**
- `index` (query, optional): Market index (`TASI` or `NOMU`). Default: `TASI`
- Backward compatibility: Existing URLs without `index` still work and default to `TASI`

**Response:**
```json
{
  "index": "TASI",
  "is_delayed": false,
  "timestamp": "2026-08-12T12:20:00+00:00",
  "index_value": 10844.12,
  "index_change": 10.94,
  "index_change_percent": 0.1,
  "total_volume": 256387075,
  "advancing": 141,
  "declining": 112,
  "unchanged": 17,
  "market_mood": "Bullish"
}
```

---

#### GET /market/gainers/?limit=1&index=TASI
Get top gaining stocks.

**Plan:** Free

**Parameters:**
- `index` (query, optional): Market index (`TASI` or `NOMU`). Default: `TASI`
- `limit` (query, optional): Number of results (default: 10, max: 50)

Results are limited to stocks with data from the most recent trading session for the selected index.

**Response:**
```json
{
  "index": "TASI",
  "is_delayed": false,
  "gainers": [
    {
      "symbol": "6040",
      "name": "شركة تبوك للتنمية الزراعية",
      "name_en": "Tabuk Agriculture Development C",
      "price": 9.13,
      "change": 0.83,
      "change_percent": 10.0,
      "volume": 4846179,
      "updated_at": "2026-08-12T13:00:00+00:00"
    }
  ],
  "count": 1
}
```

---

#### GET /market/losers/?limit=1&index=TASI
Get top losing stocks.

**Plan:** Free

**Parameters:**
- `index` (query, optional): Market index (`TASI` or `NOMU`). Default: `TASI`
- `limit` (query, optional): Number of results (default: 10, max: 50)

Results are limited to stocks with data from the most recent trading session for the selected index.

**Response:**
```json
{
  "index": "TASI",
  "is_delayed": false,
  "losers": [
    {
      "symbol": "4011",
      "name": "شركة لازوردي للمجوهرات",
      "name_en": "L'azurde Company for Jewelry SJSC",
      "price": 10.43,
      "change": -0.47,
      "change_percent": -4.31,
      "volume": 369026,
      "updated_at": "2026-08-12T13:00:00+00:00"
    }
  ],
  "count": 1
}
```

---

#### GET /market/volume/?limit=1&index=TASI
Get top stocks by trading volume.

**Plan:** Free

**Parameters:**
- `index` (query, optional): Market index (`TASI` or `NOMU`). Default: `TASI`
- `limit` (query, optional): Number of results (default: 10, max: 50)

Ranks current snapshot rows by volume; this endpoint does not apply the latest-session date filter used by gainers and losers.

**Response:**
```json
{
  "index": "TASI",
  "is_delayed": false,
  "stocks": [
    {
      "symbol": "6015",
      "name": "شركة أمريكانا للمطاعم العالمية بي إل سي - شركة أجنبية",
      "name_en": "AMERICANA",
      "price": 2.38,
      "change": 0.07,
      "change_percent": 3.03,
      "volume": 22562421,
      "updated_at": "2026-08-12T13:00:00+00:00"
    }
  ],
  "count": 1
}
```

---

#### GET /market/value/?limit=1&index=TASI
Get top stocks by trading value (SAR).

**Plan:** Free

**Parameters:**
- `index` (query, optional): Market index (`TASI` or `NOMU`). Default: `TASI`
- `limit` (query, optional): Number of results (default: 10, max: 50)

Ranks current snapshot rows by traded value; this endpoint does not apply the latest-session date filter used by gainers and losers.

**Response:**
```json
{
  "index": "TASI",
  "is_delayed": false,
  "stocks": [
    {
      "symbol": "2380",
      "name": "شركة رابغ للتكرير والبتروكيماويات",
      "name_en": "Rabigh Refining and Petrochemic",
      "price": 17.6,
      "change": 0.51,
      "change_percent": 2.98,
      "volume": 14502060,
      "value": 257478357.3,
      "updated_at": "2026-08-12T13:00:00+00:00"
    }
  ],
  "count": 1
}
```

---

#### GET /market/sectors/?index=TASI
Get sector performance.

**Plan:** Free

**Parameters:**
- `index` (query, optional): Market index (`TASI` or `NOMU`). Default: `TASI`

Returns up to 20 sectors, sorted by `change_percent` descending.

**Response:**
```json
{
  "index": "TASI",
  "is_delayed": false,
  "sectors": [
    {
      "sector_name": "Insurance",
      "sector_name_ar": "التأمين",
      "change_percent": 1.49,
      "avg_change_percent": 0.02,
      "volume": 9819397,
      "num_stocks": 26
    }
  ],
  "count": 20
}
```

**Endpoint-specific error (invalid `index`):**
```json
{
  "error": {
    "code": "INVALID_INDEX",
    "message": "Invalid index 'XYZ'. Supported values: TASI, NOMU."
  }
}
```

---

### Company / Symbol APIs

#### GET /companies/
Lightweight company directory for symbol discovery before quote and company calls. Includes Sukuk and other instrument types via `security_type`.

**Plan:** Free+

**Auth:** Requires `X-API-Key` (same as other private `/api/v1` endpoints).

**Parameters:**
- `search` (query, optional): Matches symbol, Arabic name, or English name
- `market` (query, optional): `TASI` or `NOMU` (`NOMUC` alias accepted)
- `limit` (query, optional): Number of results (default: 100, max: 500)
- `offset` (query, optional): Result offset (default: 0)

**Response:**
```json
{
  "results": [
    {
      "symbol": "2222",
      "name_ar": "أرامكو السعودية",
      "name_en": "SAUDI ARAMCO",
      "market": "TASI",
      "status": "active",
      "security_type": "Equity",
      "market_segment": "TASI",
      "is_etf": false
    }
  ],
  "count": 1,
  "total": 1,
  "limit": 1,
  "offset": 0
}
```

**`security_type` values:**
- `Equity`
- `Sukuk`
- `ETF`
- `Closed-End Fund`
- `Unknown` — source market metadata is incomplete for that symbol

**Error (invalid `market`):**
```json
{
  "error": {
    "code": "INVALID_MARKET",
    "message": "market must be one of: TASI, NOMU."
  }
}
```

**Error (invalid pagination params):**
```json
{
  "error": {
    "code": "INVALID_PARAM",
    "message": "limit and offset must be valid integers."
  }
}
```

For integer values outside the valid range, the response instead says:
`"limit must be > 0 and offset must be >= 0."`

---

#### GET /company/{symbol}/
Get company information. Response varies by plan.

**Plan:** Free (basic), Starter (full fundamentals), Pro+ (+ technicals, valuation, analysts)

**Parameters:**
- `symbol` (path, required): Stock ticker

**Data by Plan:**
- Free: name, security_type, sector_name, sector_name_ar, market_id, description, website
- Starter: + full fundamentals (PE, EPS, book value, beta, week/month/52w ranges)
- Pro+: + technicals (RSI, MACD), valuation (fair price), analysts (targets, consensus)
- `is_delayed` indicates pricing freshness: `true` for delayed prices (Free/Starter) and `false` for real-time prices (Pro/Business/Enterprise).
- `security_type` values: `Equity`, `Sukuk`, `ETF`, `Closed-End Fund`, or `Unknown` (incomplete source market metadata). Sukuk instruments are included.

**Fundamentals Fields (Starter+):**
- `float_shares` — Free float shares (tradeable)
- `week_high`, `week_low` — Highest/lowest price in last 7 days
- `month_high`, `month_low` — Highest/lowest price in last 30 days

**Response (Pro+):**
```json
{
  "symbol": "2222",
  "name": "أرامكو السعودية",
  "name_en": "SAUDI ARAMCO",
  "current_price": 26.6,
  "is_delayed": false,
  "sector_name": "Energy",
  "sector_name_ar": "الطاقة",
  "market_id": "TASI",
  "security_type": "Equity",
  "description": "Saudi Arabian Oil Company operates as an integrated energy and chemical company in the Kingdom of Saudi Arabia and internationally. The company operates through two segments, Upstream and Downstream. The Upstream segment explores, develops, produces, and sells crude oil, condensate, natural gas, and natural gas liquids (NGLs). The Downstream segment produces various chemicals, such as aromatics, olefins, and polyolefins; polyols, isocyanates, and synthetic rubber; methanol, MTBE, glycols, linear alpha olefins, polyethylene, polypropylene, polyethylene terephthalate, polyvinyl chloride, polystyrene, polycarbonate, and engineering thermoplastics and their blends; and lubricants and base oils, as well as engages in the refining and petrochemicals, retail operations, distribution, supply and trading, and power generation. It also markets and distributes hydrocarbons, petroleum products; and trades crude oil, refined petroleum, and liquid chemical products. In addition, the company develops, manufactures, and markets high-performance rubber; and provides crude oil storage, investment, consulting, information technology, personnel and other support, agri-nutrients, purchasing, engineering, benefits administration, oil field, insurance, pipeline transport, vendor sourcing, marketing and sales support, financing, support, and marine management and transportation services. Further, it engages in aircraft operations and leasing; aviation; sports club; retail fuel marketing and operations; investment management of post-employment benefit plans; wholesale fuel operations; importing and exporting refined products and crude oil; and real estate holdings. Additionally, the company engages in prospecting, exploring, drilling, processing, manufacturing, refining, extracting, and marketing hydrocarbon substances. The company was founded in 1933 and is headquartered in Dhahran, the Kingdom of Saudi Arabia.",
  "website": "https://www.aramco.com",
  "country": "Saudi Arabia",
  "currency": "SAR",
  
  "fundamentals": {
    "market_cap": 6437200000000.0,
    "pe_ratio": 15.65,
    "forward_pe": 15.93,
    "eps": 1.6998,
    "eps_ttm": 1.6998,
    "basic_eps": 1.4382,
    "diluted_eps": null,
    "book_value": 6.49,
    "price_to_book": 4.1,
    "beta": 0.01,
    "shares_outstanding": 242000000000,
    "float_shares": 6014547000,
    "week_high": 26.86,
    "week_low": 26.5,
    "month_high": 27.26,
    "month_low": 26.12,
    "fifty_two_week_high": 27.96,
    "fifty_two_week_low": 23.04
  },
  
  "technicals": {
    "rsi_14": 57.45,
    "macd_line": 0.0187,
    "macd_signal": 0.027,
    "macd_histogram": -0.0084,
    "fifty_day_average": 26.53,
    "technical_strength": 0.0,
    "price_direction": "متذبذب",
    "updated_at": "2026-08-12T12:45:00.690083+00:00"
  },
  
  "valuation": {
    "fair_price": 24.71,
    "fair_price_confidence": 0.95,
    "calculated_at": "2026-08-11T21:00:00.010275+00:00"
  },
  
  "analysts": {
    "target_mean": 30.12,
    "target_median": 29.8,
    "target_high": 35.0,
    "target_low": 26.8,
    "consensus": "buy",
    "consensus_score": 2.11,
    "num_analysts": 18
  }
}
```

---

### Historical Data

#### GET /historical/{symbol}/
Get historical OHLCV data.

**Plan:** Starter+ (interval and date-range limits vary by plan)

**Parameters:**
- `symbol` (path, required): Stock ticker or supported index code (`TASI` or `NOMU`)
- `from` (query, optional): Start date YYYY-MM-DD (default: ~30 days ago)
- `to` (query, optional): End date YYYY-MM-DD (default: today)
- `interval` (query, optional): accepted values `1d`, `1w`, `1m`, `30m`, `60m` (default: `1d`)
- `limit` (query, optional): Number of records to return (default: `500`, maximum: `2000`)
- `offset` (query, optional): Number of records to skip (default: `0`)

**Availability by plan:**
- Free: no historical access
- Starter: `1d`, `1w`, `1m`
- Pro: Starter intervals + `60m` up to 90 days
- Business: Starter intervals + `30m` up to 6 months + `60m` up to 1 year
- Enterprise: Business availability by default; custom retention, intervals, and delivery options are available by agreement

If the requested interval or date range exceeds your plan limits, the API returns `403 PLAN_LIMIT`.

**Request examples:**

```bash
curl "https://api.sahmk.sa/api/v1/historical/2222/?interval=1d&from=2024-01-01&to=2026-01-01&limit=1&offset=0" \
  -H "X-API-Key: YOUR_API_KEY"
```

```python
import requests

response = requests.get(
    "https://api.sahmk.sa/api/v1/historical/2222/",
    params={
        "interval": "1d",
        "from": "2024-01-01",
        "to": "2026-01-01",
        "limit": 1,
        "offset": 0,
    },
    headers={"X-API-Key": "YOUR_API_KEY"},
)
print(response.json())
```

```javascript
const response = await fetch(
  "https://api.sahmk.sa/api/v1/historical/2222/?interval=1d&from=2024-01-01&to=2026-01-01&limit=1&offset=0",
  { headers: { "X-API-Key": "YOUR_API_KEY" } }
);
const data = await response.json();
console.log(data);
```

**Response:**
```json
{
  "symbol": "2222",
  "interval": "1d",
  "source": "historical_eod",
  "is_intraday": false,
  "is_final": true,
  "partial": false,
  "latest_bar_at": "2024-01-01",
  "from": "2024-01-01",
  "to": "2026-01-01",
  "limit": 1,
  "offset": 0,
  "total": 500,
  "count": 1,
  "has_more": true,
  "data": [
    {
      "date": "2024-01-01",
      "open": 33.0,
      "high": 33.15,
      "low": 32.9,
      "close": 33.05,
      "volume": 12123324,
      "adjusted_close": 33.05
    }
  ]
}
```

Top-level response fields:
- `source`: Data source used to build the returned candles
- `is_intraday`: Whether the response contains intraday candles
- `is_final`: Whether the returned range is finalized
- `partial`: Whether the latest returned bar is still in progress
- `latest_bar_at`: Date or timestamp of the latest bar in the returned page
- `total`: Total records available for the query
- `count`: Records returned in this page
- `limit`: Page size used
- `offset`: Pagination offset used
- `has_more`: Whether another page is available

Pagination: while `has_more` is `true`, request the next page using `offset + limit`.

Row timestamp format:
- `30m/60m`: ISO timestamp in `date`; rows also include `turnover`, `number_of_trades`, `is_final`, and `partial`
- `1d/1w/1m`: date-based candles (`1w` and `1m` are aggregated from daily rows)

`adjusted_close` mirrors `close` for post-March-2024 and intraday records. Older historical rows may contain an adjusted value when available.

---

### Financials

#### GET /financials/{symbol}/
Access structured income statement, balance sheet, and cash flow data for Saudi listed companies.

#### Request Examples

```bash
# Starter
GET /api/v1/financials/1120/

# Pro/Business
GET /api/v1/financials/1120/?period=annual&history=1y&metrics=extended
```

#### Key Parameters

- `type` — `income`, `balance`, `cashflow`, `all`
- `period` — `annual`, `quarterly`, `auto`
- `history` — `1y`, `3y`, `5y`, `10y`, `max`
- `view` — `summary`, `full`
- `metrics` — `core`, `extended` (default: `extended`; `view=summary` resolves to core fields)
- `result` — `series`, `latest`
- `limit` — number of statement rows (default `4`, max `20`)
- `include_future_placeholders=1` — include future-dated placeholder rows (default is hidden)
- `include_partial=1` — include current incomplete annual/YTD row in annual mode

Supplying any of `view`, `history`, `metrics`, or `result` activates expanded mode. Starter cannot
use `view=full`. When `history` is supplied, it controls row count and overrides `limit`
(`result=latest` still forces one row). `history=max` is capped at 40 annual or 120 quarterly rows.

#### Auto Period Behavior

- `period=auto` resolves to `annual` when the latest fiscal year is full-year for the requested statement scope.
- `period=auto` resolves to `quarterly` when the latest fiscal year is not full-year.
- Annual history returns completed fiscal years by default; use `include_partial=1` to include the current incomplete annual/YTD row.
- Quarterly mode returns the latest available quarters by default.
- `result=latest` follows the selected/resolved granularity; in annual mode it returns the latest completed year by default unless `include_partial=1` is used.
- API default remains `period=annual` for backward compatibility.

#### Plan Access

**Starter**  
Annual statements; explicit history controls support up to 3 years. Use `period=annual` explicitly:
`period=auto` may resolve to quarterly and return `403 PLAN_LIMIT`. A bare request retains the legacy four-row extended response.

**Pro / Business**  
Quarterly financials, extended metrics, 5Y / 10Y / max history, full views.

**Enterprise**  
Custom financials feature set and access profile by agreement.

#### Notes

- Financial statements are returned directly in statement arrays (for example `income_statements`, `balance_sheets`, `cash_flows`).
- Responses include `symbol`, `statement_period`, and public reporting context in `reporting`.

#### Response Example
```json
{
  "symbol": "1120",
  "statement_period": "annual",
  "income_statements": [
    {
      "report_date": "2025-12-31",
      "statement_period": "annual",
      "fiscal_year": 2025,
      "quarters_reported": 4,
      "quarters_covered": 4,
      "is_full_year": true,
      "total_revenue": 39093965000.0,
      "gross_profit": 6730335.0,
      "operating_income": null,
      "net_income": 24791754000.0
    }
  ],
  "balance_sheets": [
    {
      "report_date": "2025-12-31",
      "statement_period": "annual",
      "fiscal_year": 2025,
      "quarters_reported": 4,
      "quarters_covered": 4,
      "is_full_year": true,
      "total_assets": 1043268297000.0,
      "total_liabilities": 900355952000.0,
      "stockholders_equity": 142912345000.0,
      "total_debt": null
    }
  ],
  "cash_flows": [
    {
      "report_date": "2025-12-31",
      "statement_period": "annual",
      "fiscal_year": 2025,
      "quarters_reported": 4,
      "quarters_covered": 4,
      "is_full_year": true,
      "operating_cash_flow": -22373072000.0,
      "investing_cash_flow": -1564467000.0,
      "financing_cash_flow": 36302349000.0,
      "free_cash_flow": null
    }
  ],
  "reporting": {
    "reporting_cadence": "quarterly",
    "quarterly_income_convention": "mixed"
  }
}
```

---

### Analytics

Compare and analyze company ratios with compact analytics endpoints.

- Default public analytics metadata is minimal.
- Ratios and compare responses include `meta.period`, `meta.metrics`, and `meta.warnings` by default.
- `results[].coverage` is not included by default on compare responses.
- Add `meta=extended` to include extra exposure metadata:
  - Ratios `meta`: `coverage`, `periods_available`, `quality`, `partial_context`
  - Compare `results[]`: `coverage`
- Ratio keys are dynamic by symbol/sector/data completeness, so render ratio keys dynamically.
- Keep frontend behavior simple: render `ratios[].ratios` and `ratios[].key_metrics` dynamically, and ignore unknown future `meta` keys safely.

#### GET /analytics/ratios/{symbol}/

Financial ratios for one symbol.

**Query Parameters**
- `history` — `latest`, `3y`, `5y`, `10y`, `max` (default: `latest`)
- `period` — `annual`, `quarterly` (default: `annual`)
- `metrics` — `core`, `extended` (default: `core`)
- `meta` — `minimal`, `extended` (default: `minimal`)

**Data Available by Plan**
- Free: no analytics access
- Starter: `latest + annual + core` only
- Pro/Business: all ratios options (`history`, `period`, `metrics`)
- Enterprise: custom ratios feature set and access profile by agreement

#### Request Examples

```bash
# Starter
GET /api/v1/analytics/ratios/1120/

# Pro/Business
GET /api/v1/analytics/ratios/1120/?history=latest&period=quarterly&metrics=extended
```

#### Ratios Response Example (Pro/Business request above)
```json
{
  "symbol": "1120",
  "ratios": [
    {
      "report_date": "2026-06-30",
      "statement_period": "quarterly",
      "fiscal_year": 2026,
      "fiscal_quarter": 2,
      "ratios": {
        "roe": 4.6,
        "roa": 0.66,
        "net_margin": 64.42,
        "revenue_growth_yoy": 13.35,
        "net_income_growth_yoy": 14.0,
        "asset_turnover": 0.0103
      },
      "key_metrics": {
        "total_revenue": 10884480000.0,
        "net_income": 7012137000.0,
        "operating_cash_flow": 10379536000.0,
        "total_assets": 1054772497000.0,
        "stockholders_equity": 152416762000.0
      }
    }
  ],
  "meta": {
    "period": "quarterly",
    "metrics": "extended",
    "warnings": [
      "Some metrics unavailable"
    ]
  }
}
```

#### GET /analytics/compare/

Compare ratio snapshots across multiple symbols.

**Query Parameters**
- `symbols` — required comma-separated symbols (example: `1120,1180,1010`)
- `metrics` — `core`, `extended` (default: `core`)
- `meta` — `minimal`, `extended` (default: `minimal`)
- `strict` — boolean (default: `false`); when true, omit symbols whose latest ratio snapshot is incomplete

**Data Available by Plan**
- Starter: up to 3 symbols + `core` metrics only
- Pro: up to 10 symbols + `core`/`extended` metrics
- Business: up to 20 symbols + `core`/`extended` metrics
- Enterprise: custom symbol limits and compare feature profile by agreement

#### Request Examples
```bash
# Starter
GET /api/v1/analytics/compare/?symbols=1120,1180,1010

# Pro
GET /api/v1/analytics/compare/?symbols=1120&metrics=extended
```

#### Compare Response Example
```json
{
  "results": [
    {
      "symbol": "1120",
      "company_name": "مصرف الراجحي",
      "sector_name": "Banks",
      "sector_name_ar": "البنوك",
      "market_id": "TASI",
      "market_cap": 384600000000.0,
      "current_price": 64.05,
      "ratios": {
        "roe": 9.48,
        "roa": 1.37,
        "net_margin": 67.49,
        "asset_turnover": 0.0203
      },
      "key_metrics": {
        "total_revenue": 21412480000.0,
        "net_income": 14452137000.0,
        "total_assets": 1054772497000.0,
        "stockholders_equity": 152416762000.0
      }
    }
  ],
  "count": 1,
  "meta": {
    "period": "annual",
    "metrics": "extended",
    "warnings": [
      "Some metrics unavailable"
    ]
  }
}
```

---

### Dividends

#### GET /dividends/{symbol}/
Get dividend history and yield.

**Plan:** Starter+

**Parameters:**
- `symbol` (path, required): Stock ticker
- `limit` (query, optional): Number of records (default: 10, max: 50)

**Response:**
```json
{
  "symbol": "2222",
  "current_price": 26.6,
  "trailing_12m_yield": 5.07,
  "trailing_12m_dividends": 1.3491,
  "payments_last_year": 4,
  "upcoming": [
    {
      "value": 0.3393,
      "period": "Q2",
      "eligibility_date": "2026-08-19",
      "distribution_date": "2026-08-27"
    }
  ],
  "history": [
    {
      "value": 0.3393,
      "value_percent": null,
      "period": "Q2",
      "fiscal_year": "2026",
      "announcement_date": "2026-08-04",
      "eligibility_date": "2026-08-19",
      "distribution_date": "2026-08-27"
    }
  ]
}
```

---

### Stock Events

#### GET /events/
Get AI-generated stock event summaries.

**Plan:** Pro+

**Parameters:**
- `symbol` (query, optional): Filter by stock ticker
- `type` (query, optional): Filter by event type (UPPERCASE)
- `importance` (query, optional): Filter by importance (`CRITICAL`, `IMPORTANT`, `REGULAR`)
- `limit` (query, optional): Number of results (default: 20, max: 100)
- `offset` (query, optional): Result offset (default: 0)

**Response:**
```json
{
  "events": [
    {
      "symbol": "4190",
      "stock_name": "مكتبة جرير",
      "event_type": "MARKET_EXPANSION",
      "importance": "important",
      "sentiment": "positive",
      "description": "افتتحت مكتبة جرير معرضاً جديداً بمطار الملك فهد الدولي في الدمام، وهو المعرض التاسع والستون داخل المملكة، ويعد الخامس خلال عام 2026، باستثمارات بلغت 2 مليون ريال سعودي.",
      "event_date": "2026-08-10",
      "article_date": "2026-08-10T13:14:06.653295+00:00",
      "created_at": "2026-08-10T13:14:10.917105+00:00"
    }
  ],
  "count": 1,
  "total": 78,
  "limit": 1,
  "offset": 0,
  "has_more": true,
  "available_types": [
    "FINANCIAL_REPORT", "DIVIDEND_ANNOUNCEMENT", "STOCK_SPLIT",
    "MERGER_ACQUISITION", "MANAGEMENT_CHANGE", "NEW_LISTING", "DELISTING",
    "REGULATORY_ACTION", "PRODUCT_LAUNCH", "PARTNERSHIP", "LEGAL_ISSUE",
    "MARKET_EXPANSION", "RESTRUCTURING", "EARNINGS_SURPRISE", "INSIDER_TRADING",
    "ANALYST_RATING_CHANGE", "CAPITAL_INCREASE", "SHAREHOLDER_MEETING", "OTHER"
  ]
}
```

**Notes:**
- `stock_name` can be `null` for some events
- `article_date` can be `null` when the source article has no publication timestamp
- `event_type` values are UPPERCASE
- `available_types` is server-defined and may expand in future releases
- `sentiment` values: `very_positive`, `positive`, `slightly_positive`, `neutral`, `slightly_negative`, `negative`, `very_negative`
- `importance` values: `critical`, `important`, `regular`

---

## WebSocket Streaming

Real-time streaming via WebSocket. Pro, Business, and Enterprise plans only.
Payloads in this section are protocol references and are not live-sampled.

### Stocks Channel

#### Connection

```
wss://api.sahmk.sa/ws/v1/stocks/?api_key=YOUR_API_KEY
```

**Plan:** Pro, Business, or Enterprise

#### Subscription Limits

| Plan | Max symbols/connection | Max symbols/call | Subscribe all (*) |
|------|------------------------|------------------|-------------------|
| Pro | 60 | 20 | ❌ |
| Business | 120 | 40 | ❌ |
| Enterprise | 200 | Up to 100 | ✅ |

**Notes:**
- Use multiple connections to exceed your plan's per-connection cap.
- Limits are also returned in the initial `connected` message under `limits`.

#### Client → Server Messages

| Action | Message | Description |
|--------|---------|-------------|
| Subscribe | `{"action": "subscribe", "symbols": ["2222", "1120"]}` | Subscribe to specific stocks |
| Subscribe All | `{"action": "subscribe", "symbols": ["*"]}` | Subscribe to all stocks (Enterprise only) |
| Unsubscribe | `{"action": "unsubscribe", "symbols": ["2222"]}` | Stop receiving updates for symbols |
| Ping | `{"action": "ping"}` | Keep-alive |

#### Server → Client Messages

| Type | Description |
|------|-------------|
| `connected` | Connection confirmed with plan and limits |
| `subscribed` | Subscription confirmed |
| `unsubscribed` | Unsubscribe confirmed |
| `quote` | Real-time price update |
| `pong` | Ping response |
| `error` | Error message |

### Subscribed Message Format

```json
{
  "type": "subscribed",
  "symbols": ["1120", "2222"],
  "total": 2,
  "limit": 120
}
```

### Connected Message Format

```json
{
  "type": "connected",
  "plan": "business",
  "delivery_profile": "business_standard",
  "limits": {
    "max_symbols_per_connection": 120,
    "max_symbols_per_call": 40,
    "stream_modes": ["standard"]
  },
  "message": "Connected to SAHMK real-time stock stream",
  "timestamp": "2026-02-10T10:00:00.000Z"
}
```

### Quote Message Format

```json
{
  "type": "quote",
  "symbol": "2222",
  "mode": "standard",
  "timestamp": "2026-02-10T10:30:15.123Z",
  "latency_ms": 42,
  "data": {
    "price": 25.86,
    "open": 25.60,
    "high": 25.86,
    "low": 25.60,
    "close": 25.86,
    "change": 0.18,
    "change_percent": 0.7,
    "previous_close": 25.68,
    "volume": 9803705,
    "value": 252308343.0,
    "bid": 25.82,
    "bid_size": 79,
    "ask": 25.86,
    "ask_size": 188,
    "market_session": "REGULAR",
    "liquidity": {
      "inflow_value": 184950463.03,
      "inflow_volume": 7182468,
      "outflow_value": 67357881.91,
      "outflow_volume": 2621237,
      "net_value": 117592581.12
    },
    "trade_time": "2026-02-10T10:30:12+00:00"
  }
}
```

**WebSocket Quote Fields:**
| Field | Description |
|-------|-------------|
| `price` | Current price |
| `change` / `change_percent` | Price change |
| `previous_close` | Yesterday's close |
| `volume` / `value` | Trading volume & turnover (SAR) |
| `bid` / `ask` | Best bid/ask prices |
| `bid_size` / `ask_size` | Optional quantity at best bid/ask |
| `liquidity.*` | Money-flow values and volumes. REST quotes additionally include `inflow_trades` and `outflow_trades`; those trade-count fields are not sent on WebSocket quotes. |

### JavaScript Example

```javascript
const API_KEY = "shmk_live_xxxxxxxxxxxxxxxx";
const ws = new WebSocket(`wss://api.sahmk.sa/ws/v1/stocks/?api_key=${API_KEY}`);

ws.onopen = () => {
  ws.send(JSON.stringify({
    action: "subscribe",
    symbols: ["2222", "1120", "4191"]
  }));
};

ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);

  if (msg.type === "connected") {
    console.log("Plan:", msg.plan, "Limits:", msg.limits);
  }

  if (msg.type === 'quote') {
    console.log(`${msg.symbol}: ${msg.data.price} (${msg.data.change_percent}%)`);
  }
};

// Keep-alive ping every 30 seconds
setInterval(() => {
  if (ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ action: "ping" }));
  }
}, 30000);
```

### Python Example

```python
import asyncio
import websockets
import json

API_KEY = "shmk_live_xxxxxxxxxxxxxxxx"

async def stream_stocks():
    uri = f"wss://api.sahmk.sa/ws/v1/stocks/?api_key={API_KEY}"
    
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({
            "action": "subscribe",
            "symbols": ["2222", "1120", "4191"]
        }))
        
        async for message in ws:
            data = json.loads(message)
            if data["type"] == "quote":
                print(f"{data['symbol']}: {data['data']['price']}")

asyncio.run(stream_stocks())
```

### Trades Channel

Stream live trades. An explicit-symbol subscribe returns `subscribed`, then one
`trades_snapshot` per newly subscribed symbol, followed by live `trade` updates.

#### Connection

```
wss://api.sahmk.sa/ws/v1/market/trades/?api_key=YOUR_API_KEY
```

Optional: add `&symbol=2222` to auto-subscribe on connect.

**Plan:** Pro, Business, or Enterprise

If an existing Best Price access record is suspended, revoked, expired, or overdue for required
reporting or invoicing, the trades connection is rejected with close code 4403 until the account
state is resolved.

#### Subscription Limits

| Plan | Max symbols/connection | Max symbols/call | Subscribe all (*) |
|------|------------------------|------------------|-------------------|
| Pro | 60 | 20 | ❌ |
| Business | 120 | 40 | ❌ |
| Enterprise | 200 | Up to 100 | ✅ |

#### Client → Server Messages

| Action | Message | Description |
|--------|---------|-------------|
| Subscribe | `{"action": "subscribe", "symbols": ["2222", "1120"]}` | Subscribe to trades |
| Subscribe All | `{"action": "subscribe", "symbols": ["*"]}` | Subscribe to all symbols (Enterprise only) |
| Unsubscribe | `{"action": "unsubscribe", "symbols": ["2222"]}` | Stop receiving updates |
| Snapshot | `{"action": "snapshot", "symbol": "2222", "limit": 50}` | Request recent trades (`limit` default 50, max 200) |
| Ping | `{"action": "ping"}` | Keep-alive |

#### Server → Client Messages

| Type | Description |
|------|-------------|
| `connected` | Connection confirmed with plan and limits |
| `subscribed` | Subscription confirmed |
| `unsubscribed` | Unsubscribe confirmed |
| `trades_snapshot` | Recent trades for a symbol |
| `trade` | Live trade update |
| `pong` | Ping response |
| `error` | Error message |

#### Subscribed Message Format

```json
{
  "type": "subscribed",
  "symbols": ["1120", "2222"],
  "total": 2,
  "limit": 60,
  "subscribe_all": false
}
```

#### Connected Message Format

```json
{
  "type": "connected",
  "channel": "trades",
  "plan": "pro",
  "delivery_profile": "standard",
  "limits": {
    "max_symbols_per_connection": 60,
    "max_symbols_per_call": 20,
    "snapshot_limit_max": 200
  },
  "message": "Connected to SAHMK real-time trades stream",
  "timestamp": "2026-07-28T09:31:58.197050+00:00"
}
```

#### Trade Message Format

```json
{
  "type": "trade",
  "symbol": "2222",
  "event_time": "2026-07-28T09:31:58+00:00",
  "price": 26.32,
  "quantity": 10,
  "value": 263.2,
  "market_session": "REGULAR",
  "timestamp": "2026-07-28T09:31:58.774829+00:00"
}
```

### Depth Channel

Stream live order-book depth. Requires a Pro, Business, or Enterprise plan plus approved Market Depth access.

#### Connection

```
wss://api.sahmk.sa/ws/v1/market/depth/?api_key=YOUR_API_KEY
```

Optional: add `&symbol=2222` to receive `connected` followed by an initial `depth_snapshot`.

#### Subscription Limits

| Plan | Max symbols/connection | Max symbols/call | Entitled levels | Subscribe all (*) |
|------|------------------------|------------------|-----------------|-------------------|
| Pro | 60 | 20 | 5 | ❌ |
| Business | 120 | 40 | Up to 20 | ❌ |
| Enterprise | 200 | Up to 100 | Up to 20 | ✅ |

Use `connected.limits` and `connected.entitled_levels` as runtime truth.

#### Client → Server Messages

| Action | Message |
|--------|---------|
| Subscribe | `{"action":"subscribe","symbols":["2222","1120"],"levels":20}` |
| Subscribe All | `{"action":"subscribe","symbols":["*"],"levels":20}` (Enterprise only) |
| Unsubscribe | `{"action":"unsubscribe","symbols":["1120"]}` |
| Snapshot | `{"action":"snapshot","symbol":"2222","levels":5}` |
| Ping | `{"action":"ping"}` |

#### Message Ordering

- Explicit symbols: one `depth_snapshot` per symbol, then `subscribed`.
- Enterprise wildcard: `subscribed` first, then the initial snapshot burst.
- Ongoing live updates are also `depth_snapshot` messages.

#### Connected Message Format

```json
{
  "type": "connected",
  "channel": "depth",
  "symbol": null,
  "plan": "enterprise",
  "entitled_levels": 20,
  "limits": {
    "max_symbols_per_connection": 200,
    "max_symbols_per_call": 20,
    "wildcard_allowed": true
  },
  "timestamp": "2026-07-09T15:05:37.840967+00:00"
}
```

Customer connections do not receive a `mode` field in this message.

#### Subscribed Message Format

```json
{
  "type": "subscribed",
  "symbols": ["1120", "2222"],
  "total": 2,
  "limit": 200
}
```

#### Depth Snapshot Format

```json
{
  "type": "depth_snapshot",
  "symbol": "2222",
  "available": true,
  "updated_at": "2026-07-09T15:05:37.840967+00:00",
  "session": "postmarket",
  "book_state": "normal",
  "levels": 5,
  "best_bid": 26.68,
  "best_ask": 26.72,
  "spread": 0.04,
  "spread_bps": 14.99,
  "total_bid_quantity_top5": 29085,
  "total_ask_quantity_top5": 504644,
  "total_bid_quantity": 29085,
  "total_ask_quantity": 504644,
  "level_imbalance": -0.891,
  "level_imbalance_top5": -0.891,
  "bids": [{ "level": 0, "price": 26.68, "quantity": 79, "order_count": 10 }],
  "asks": [{ "level": 0, "price": 26.72, "quantity": 41188, "order_count": 38 }],
  "entitled_levels": 20,
  "timestamp": "2026-07-09T15:05:37.872738+00:00"
}
```

When no current book is available, the snapshot contains `available: false` and a human-readable `message`;
clients must not assume bid and ask arrays are present.

### WebSocket Error Codes

| Code | Meaning |
|------|---------|
| 4000 | Internal connection failure. Retry with exponential backoff and jitter. |
| 4401 | Authentication failure. Stop retrying and fix the API key. |
| 4403 | Access or entitlement failure. Stop retrying until the account or plan issue is resolved. |
| 4429 | Temporary throttle. Retry with backoff and jitter, honoring `retry_after_seconds` when provided. |

Action-level failures arrive as `type: "error"` messages while the socket remains open. Codes are
channel-specific and case-sensitive:

- Stocks/quotes: `subscribe_rate_limited`, `subscribe_call_limit`, `subscription_limit`,
  `symbols_required`, and `plan_not_entitled`. An unknown stocks action can return an error message
  without a `code`.
- Trades: `snapshot_rate_limited`, `symbol_required`, `unknown_action`, and `wildcard_not_allowed`.
- Depth: uppercase `DEPTH_WS_*` codes including `DEPTH_WS_ACTION_RATE_LIMITED`, plus
  `SYMBOL_REQUIRED` and `UNKNOWN_ACTION`.

Developer accounts must be email-verified. Unverified accounts are rejected with close code 4403
(`unverified_account` on stocks/trades and `ACCOUNT_UNVERIFIED` on depth).

### Update Frequency

- Updates are pushed as data changes during active trading sessions
- Only changed symbols are pushed (no redundant data)
- You may keep WebSocket connections open outside market hours; SAHMK does not intentionally disconnect clients at market close
- While connected off-hours, continue sending a ping every 30 seconds
- After a disconnect, reconnect with capped exponential backoff and jitter, then restore all subscriptions
- Market events may be absent while the market is inactive

---

## Realtime Event Engine v1

Realtime Event Engine v1 is the next step of the existing webhook + price alert workflow.
Use it to define event rules, deliver webhook notifications, and inspect delivery history.
Request and payload examples in this section are protocol references and are not live-sampled.

### Supported Event Types

- `price_alert`
- `large_move`
- `abnormal_volume`
- `unusual_value_traded`

### Endpoint Summary

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET / POST | `/api/v1/webhooks/` | List or register webhook destinations |
| DELETE | `/api/v1/webhooks/{id}/` | Delete a webhook destination |
| POST | `/api/v1/webhooks/{id}/verify/` | Retry destination verification |
| POST | `/api/v1/webhooks/{id}/test-delivery/` | Send a signed synthetic test event |
| GET / POST | `/api/v1/alerts/` | List or create event rules |
| GET / PATCH / DELETE | `/api/v1/alerts/{id}/` | Inspect, update, or delete a rule |
| GET | `/api/v1/alerts/symbol-context/` | Fetch null-safe symbol context for rule builders |

---

### POST /api/v1/webhooks/

Register a webhook destination for Realtime Event Engine callbacks.

**Headers**
- `X-API-Key: YOUR_API_KEY`
- `Content-Type: application/json`

**Request Body**
- `url` (string, required): HTTPS callback URL
- `name` (string, optional): Display name

#### Example Request

```bash
curl -X POST "https://api.sahmk.sa/api/v1/webhooks/" \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/hooks/sahmk",
    "name": "Trading Prod"
  }'
```

```python
import requests

response = requests.post(
    "https://api.sahmk.sa/api/v1/webhooks/",
    headers={
        "X-API-Key": "YOUR_API_KEY",
        "Content-Type": "application/json"
    },
    json={
        "url": "https://example.com/hooks/sahmk",
        "name": "Trading Prod"
    }
)
print(response.json())
```

```javascript
const response = await fetch("https://api.sahmk.sa/api/v1/webhooks/", {
  method: "POST",
  headers: {
    "X-API-Key": "YOUR_API_KEY",
    "Content-Type": "application/json"
  },
  body: JSON.stringify({
    url: "https://example.com/hooks/sahmk",
    name: "Trading Prod"
  })
});

console.log(await response.json());
```

#### Example Response

```json
{
  "id": 19,
  "url": "https://example.com/hooks/sahmk",
  "name": "Trading Prod",
  "signing_secret": "xxxxxxxxxxxxxxxx",
  "is_verified": false,
  "is_active": true,
  "created_at": "2026-05-08T13:30:12+03:00"
}
```

On registration, SAHMK sends `{"event":"webhook.verify","challenge":"..."}` to the destination.
Return HTTP 200 to complete verification. Unverified destinations do not receive live events and
the registration response may include a top-level `warning`. Retry verification with
`POST /api/v1/webhooks/{id}/verify/`.

---

### POST /api/v1/alerts/

Create a Realtime Event Engine rule (the evolved version of a price alert).

**Headers**
- `X-API-Key: YOUR_API_KEY`
- `Content-Type: application/json`

**Request Body**
- `symbol` (string, required for single-symbol rules): Stock symbol (example: `2222`)
- `target_scope_type` (optional): `single_symbol` (default) or `static_symbol_list`
- `symbols` (array, required for `static_symbol_list`): Up to 30 symbols on Pro or 100 on Business
- `event_type` (string, required): `price_alert`, `large_move`, `abnormal_volume`, `unusual_value_traded`
- `condition` (string): Required for `price_alert`; optional and normalized for the other documented types
- `value` (number, required): numeric threshold
- `webhook_id` (integer): Legacy shorthand for a webhook destination
- `destination` (object): Unified destination with `type: webhook|email|whatsapp` and type-specific fields
- `once` (boolean, optional, default `true`): When `true`, rule auto-deactivates after first trigger
- `config` (object, optional): deterministic options (for example `window` for `large_move`)

The examples below explicitly set `once=false` to create recurring rules, so their responses show
`fire_once: false`. Omit `once` to use the default one-trigger behavior.

**Condition rules**
- `price_alert`: `price_above`, `price_below`, `pct_change`
- `large_move`: normalized to `pct_change_abs_gte`; `config.window` defaults to `5m`; maximum threshold is 10% for TASI and 30% for NOMU
- `abnormal_volume`: normalized to `ratio_gte`; `value` must be greater than `1.0`; baseline defaults to `rolling_reference`
- `unusual_value_traded`: normalized to `ratio_gte`; `value` must be greater than `1.0`; baseline defaults to `rolling_reference`

Email and WhatsApp destinations force one-shot behavior (`fire_once: true`). Email must match the
developer account email; WhatsApp requires the verified account number.

#### Example Request

```bash
curl -X POST "https://api.sahmk.sa/api/v1/alerts/" \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "2222",
    "event_type": "large_move",
    "condition": "pct_change_abs_gte",
    "value": 3.0,
    "webhook_id": 19,
    "once": false,
    "config": { "window": "15m" }
  }'
```

```python
import requests

response = requests.post(
    "https://api.sahmk.sa/api/v1/alerts/",
    headers={"X-API-Key": "YOUR_API_KEY"},
    json={
        "symbol": "2222",
        "event_type": "large_move",
        "condition": "pct_change_abs_gte",
        "value": 3.0,
        "webhook_id": 19,
        "once": False,
        "config": {"window": "15m"}
    }
)
print(response.json())
```

```javascript
const response = await fetch("https://api.sahmk.sa/api/v1/alerts/", {
  method: "POST",
  headers: {
    "X-API-Key": "YOUR_API_KEY",
    "Content-Type": "application/json"
  },
  body: JSON.stringify({
    symbol: "2222",
    event_type: "large_move",
    condition: "pct_change_abs_gte",
    value: 3.0,
    webhook_id: 19,
    once: false,
    config: { window: "15m" }
  })
});

console.log(await response.json());
```

#### Practical Rule Examples

```bash
# 1) Large move rule (>= 3% absolute move in 15m)
curl -X POST "https://api.sahmk.sa/api/v1/alerts/" \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "2222",
    "event_type": "large_move",
    "condition": "pct_change_abs_gte",
    "value": 3.0,
    "webhook_id": 19,
    "once": false,
    "config": { "window": "15m" }
  }'

# 2) Abnormal volume rule (>= 2.5x baseline volume)
curl -X POST "https://api.sahmk.sa/api/v1/alerts/" \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "2010",
    "event_type": "abnormal_volume",
    "condition": "ratio_gte",
    "value": 2.5,
    "webhook_id": 19,
    "once": false
  }'

# 3) Unusual traded value rule (>= 3.0x traded value baseline)
curl -X POST "https://api.sahmk.sa/api/v1/alerts/" \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "1180",
    "event_type": "unusual_value_traded",
    "condition": "ratio_gte",
    "value": 3.0,
    "webhook_id": 19,
    "once": false
  }'
```

#### Example Response

```json
{
  "id": 42,
  "workspace_id": null,
  "symbol": "2222",
  "event_type": "large_move",
  "target_scope_type": "single_symbol",
  "target_scope_id": null,
  "symbols": ["2222"],
  "evaluated_symbol_rules": 1,
  "condition": "pct_change_abs_gte",
  "value": "3.0",
  "config": {
    "window": "15m",
    "destination": { "type": "webhook", "webhook_id": 19 }
  },
  "webhook_id": 19,
  "webhook_url": "https://example.com/hooks/sahmk",
  "destination": { "type": "webhook", "webhook_id": 19 },
  "status": "active",
  "fire_once": false,
  "last_triggered_at": null,
  "total_triggers": 0,
  "created_at": "2026-05-08T13:36:45+03:00"
}
```

---

### GET /api/v1/alerts/

List event rules for your account.

**Query Parameters**
- `status` (optional): `active`, `paused`, `all` (default: `active`)

Status values returned on each rule include `active`, `paused`, and `triggered`.

#### Example Request

```bash
curl "https://api.sahmk.sa/api/v1/alerts/?status=active" \
  -H "X-API-Key: YOUR_API_KEY"
```

```python
import requests

response = requests.get(
    "https://api.sahmk.sa/api/v1/alerts/",
    headers={"X-API-Key": "YOUR_API_KEY"},
    params={"status": "active"}
)
print(response.json())
```

```javascript
const query = new URLSearchParams({
  status: "active"
});

const response = await fetch(
  `https://api.sahmk.sa/api/v1/alerts/?${query}`,
  { headers: { "X-API-Key": "YOUR_API_KEY" } }
);

console.log(await response.json());
```

#### Example Response

```json
{
  "alerts": [
    {
      "id": 42,
      "workspace_id": null,
      "symbol": "2222",
      "event_type": "large_move",
      "target_scope_type": "single_symbol",
      "target_scope_id": null,
      "symbols": ["2222"],
      "evaluated_symbol_rules": 1,
      "condition": "pct_change_abs_gte",
      "value": "3.0",
      "config": {
        "window": "15m",
        "destination": { "type": "webhook", "webhook_id": 19 }
      },
      "status": "active",
      "fire_once": false,
      "webhook_id": 19,
      "webhook_url": "https://example.com/hooks/sahmk",
      "destination": { "type": "webhook", "webhook_id": 19 },
      "last_triggered_at": null,
      "total_triggers": 0,
      "created_at": "2026-05-08T13:36:45+03:00"
    }
  ]
}
```

---

### Event history availability

Event history is available in the authenticated Developer Dashboard. There is currently no public
`X-API-Key` route at `/api/v1/events/history/`; do not integrate against that path.

---

### Webhook Payload Schema

Realtime Event Engine webhook payloads use one canonical envelope across event types:

```json
{
  "event_id": "9a6b8f22-2d1d-4b3f-b75f-7f9d5f101234",
  "event_type": "large_move",
  "symbol": "2222",
  "detected_at": "2026-05-08T13:48:22+03:00",
  "severity": "warning",
  "title": "Large move detected",
  "summary": "Price moved more than configured threshold in the selected window.",
  "metrics": {
    "price": 25.86,
    "pct_change": 3.4,
    "volume": 9803705,
    "value": 252308343.0,
    "avg_volume": 8243000,
    "reference_value": 245000000.0,
    "rolling_volume_baseline": 4100000,
    "rolling_value_baseline": 120000000.0,
    "baseline_source": "rolling_window",
    "baseline_sample_count": 30,
    "volume_baseline_sample_count": 30,
    "value_baseline_sample_count": 30,
    "high": 25.86,
    "low": 25.60,
    "change": 0.85,
    "window": "15m",
    "threshold": 3.0
  },
  "conditions_matched": {
    "window": "15m",
    "operator": "abs>=",
    "observed_pct_change": 3.4,
    "threshold_pct": 3.0,
    "baseline_price": 25.01,
    "current_price": 25.86
  },
  "correlation_id": "large_move:2222:29650608",
  "version": "v1",
  "destination": {
    "type": "webhook",
    "webhook_id": 19,
    "webhook_url": "https://example.com/hooks/sahmk"
  }
}
```

**Notes**
- Top-level envelope keys are always included.
- `metrics` is always present; many metric values may be `null` depending on event context.
- `conditions_matched` is always present as an object but may be empty in some events.
- `severity` is `info`, `warning`, or `critical`.
- `correlation_id` uses `{event_type}:{symbol}:{unix_minute_bucket}`.
- `destination` is always present with webhook, email, or WhatsApp delivery metadata.
- Ignore unknown keys for forward compatibility.

### Event-specific `conditions_matched` shape

```json
{
  "price_alert": {
    "operator": ">",
    "observed": 26.1,
    "threshold": 26.0
  },
  "large_move": {
    "window": "15m",
    "operator": "abs>=",
    "observed_pct_change": 3.4,
    "threshold_pct": 3.0,
    "baseline_price": 25.01,
    "current_price": 25.86
  },
  "abnormal_volume": {
    "event_type": "abnormal_volume",
    "operator": ">=",
    "metric": "volume_ratio",
    "current_value": 9803705,
    "baseline_value": 4100000,
    "ratio": 2.39,
    "threshold": 2.0
  },
  "unusual_value_traded": {
    "event_type": "unusual_value_traded",
    "operator": ">=",
    "metric": "value_ratio",
    "current_value": 252308343.0,
    "baseline_value": 120000000.0,
    "ratio": 2.1,
    "threshold": 2.0
  }
}
```

Numeric encoding is JSON number (not string). `ratio` and `observed_pct_change` are rounded to 4 decimals.

Important: `unusual_value_traded` matching uses `value / rolling_value_baseline` (not `reference_value`).

### Webhook Signing (`X-SAHMK-Signature`)

Each delivery includes:

- `X-SAHMK-Signature`: `t=<unix_ts>,v1=<hex_hmac>`
- `X-SAHMK-Event`
- `X-SAHMK-Event-Id`

Compute expected signature:
- Serialize JSON with sorted keys and no extra whitespace.
- Build signed payload as: `<timestamp>.<canonical_json>`
- Compute `v1` as lowercase hex HMAC-SHA256 over UTF-8 bytes.

#### Python Verification Example

```python
import hmac
import hashlib
import json

def verify_signature(secret, payload_dict, header_value):
    # header format: t=1715523245,v1=<hex>
    parts = dict(part.split("=", 1) for part in header_value.split(","))
    timestamp = parts["t"]
    incoming_signature = parts["v1"]

    canonical_json = json.dumps(payload_dict, sort_keys=True, separators=(",", ":"))
    signed_payload = f"{timestamp}.{canonical_json}".encode("utf-8")
    expected = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, incoming_signature)
```

#### JavaScript Verification Example

```javascript
import crypto from "crypto";

function verifySignature(secret, payload, signatureHeader) {
  // signatureHeader format: "t=1715523245,v1=<hex>"
  const parts = Object.fromEntries(
    signatureHeader.split(",").map((part) => part.split("=", 2))
  );
  const timestamp = parts.t;
  const incomingSignature = parts.v1;

  // Use a canonical JSON serializer that sorts keys and removes extra whitespace.
  const canonicalJson = canonicalStringify(payload);
  const signedPayload = `${timestamp}.${canonicalJson}`;
  const expected = crypto
    .createHmac("sha256", secret)
    .update(signedPayload, "utf8")
    .digest("hex");

  return crypto.timingSafeEqual(
    Buffer.from(expected, "utf8"),
    Buffer.from(incomingSignature, "utf8")
  );
}
```

### Delivery & Retry Behavior

- State flow: `pending -> retrying -> delivered | dead_letter`
- Retry delays: `2s`, `10s`, `60s`
- Attempts: `4` total (initial + 3 retries)
- Retry trigger: all non-2xx outcomes are retried (4xx, 5xx, timeout, connection errors)
- No jitter is currently applied
- No public replay endpoint is currently available for dead-letter events
- After 3 consecutive failed deliveries, the webhook is deactivated. Resolve the endpoint issue and re-verify it before using associated rules again.

---

## Rate Limits

| Plan | Daily Limit | Burst Limit | API Keys | WebSocket | Event Webhooks | Event Rules |
|---|---:|---:|---:|:---:|---:|---:|
| Free | 100/day | 10/min | 1 | ✗ | 0 | 0 |
| Starter | 5,000/day | 100/min | 3 | ✗ | 0 | 0 |
| Pro | 50,000/day | 500/min | 10 | ✓ | 3 | 10 |
| Business | 150,000/day | 1,000/min | 30 | ✓ | 10 | 50 |
| Enterprise | Custom | Custom | Custom | ✓ | Custom | Custom |

Daily quotas are shared across the account, including Live and Test keys. Rotating or revoking a key does not create a new daily pool.

**Burst Protection:** To prevent abuse and protect stability, per-minute throttling is applied at both API-key and account levels. Requests exceeding these limits return HTTP 429. Daily limits reset at midnight in Asia/Riyadh (UTC+3). Enterprise limits are contract-based and may be monthly quotas or resource-based.

### Rate Limit Headers

Most successful `/api/v1/*` responses include:

- `X-RateLimit-Limit`: plan daily limit
- `X-RateLimit-Remaining`: plan daily limit minus the current key's stored request count
- `X-RateLimit-Reset`: Unix timestamp for the next Asia/Riyadh midnight

The daily quota is enforced account-wide by aggregating usage across all keys. However,
`X-RateLimit-Remaining` is currently derived from the key used for the request, so with multiple
keys it can be higher than the account's true remaining quota. Edge proxies may strip headers, so
use `HTTP 429`, the response `detail`, and `Retry-After` when present as the fallback throttle contract.

---

## Error Codes

| HTTP Code | Error Code | Description |
|-----------|------------|-------------|
| 400 | INVALID_ROUTE | Wrong endpoint path; response includes suggested correct route |
| 401 | — | Missing `X-API-Key`; response uses a `detail` string |
| 403 | — | Invalid format or invalid/revoked API key; response uses a `detail` string |
| 403 | PLAN_LIMIT | Endpoint requires higher plan |
| 404 | INVALID_SYMBOL | Exchange symbol not found |
| 404 | INVALID_IDENTIFIER | Identifier query did not resolve |
| 409 | AMBIGUOUS_IDENTIFIER | Identifier query matched multiple companies |
| 409 | PRICE_DATA_TEMPORARILY_UNAVAILABLE | Symbol exists but its current price row is unavailable; retry shortly |
| 429 | — | Daily, burst, IP, or temporary security throttle; response uses a `detail` string |
| 500 | SERVER_ERROR | Internal server error |

Some new free accounts may temporarily hit a security limit.  
If you receive `HTTP 429` with a `detail` containing `Temporary security limit reached`, honor `Retry-After` when present and try again later.

### Common Integration Error: Wrong Batch Quote Route

If a client calls `GET /api/v1/quote/batch/` by mistake, the API returns `400 INVALID_ROUTE` with route guidance instead of an `INVALID_SYMBOL` for `"BATCH"`.

```json
{
  "error": {
    "code": "INVALID_ROUTE",
    "message": "Did you mean /api/v1/quotes/?symbols=2222,1120 ?"
  }
}
```

### Error Response Formats

Endpoint validation and lookup errors generally use a structured `error` object:

```json
{
  "error": {
    "code": "INVALID_SYMBOL",
    "message": "Stock symbol '9999' not found."
  }
}
```

Standard REST authentication and throttle failures use a top-level `detail` string:

```json
{
  "detail": "Request was throttled. Expected available in 60 seconds."
}
```

Event Engine endpoints (`/webhooks/` and `/alerts/`) use a structured missing-key response:

```json
{
  "error": {
    "code": "AUTH_REQUIRED",
    "message": "X-API-Key header is required."
  }
}
```

Alert rule validation uses an `error.details` field map:

```json
{
  "error": {
    "code": "VALIDATION",
    "details": {
      "value": "For ratio event types, value must be greater than 1.0."
    }
  }
}
```

---

## Quick Start

```bash
# Get Aramco quote by symbol
curl "https://api.sahmk.sa/api/v1/quote/2222/" \
  -H "X-API-Key: YOUR_API_KEY"

# Resolve by name/alias using optional identifier query param
curl "https://api.sahmk.sa/api/v1/quote/2222/?identifier=%D8%A3%D8%B1%D8%A7%D9%85%D9%83%D9%88" \
  -H "X-API-Key: YOUR_API_KEY"

# Get multiple quotes
curl "https://api.sahmk.sa/api/v1/quotes/?symbols=2222,1120,2010" \
  -H "X-API-Key: YOUR_API_KEY"

# Batch by names/aliases
curl "https://api.sahmk.sa/api/v1/quotes/?identifiers=Aramco,%D8%A7%D9%84%D8%B1%D8%A7%D8%AC%D8%AD%D9%8A" \
  -H "X-API-Key: YOUR_API_KEY"

# Discover companies/symbols
curl "https://api.sahmk.sa/api/v1/companies/?search=aramco&market=TASI&limit=20" \
  -H "X-API-Key: YOUR_API_KEY"

# Get market summary (defaults to TASI if index is omitted)
curl "https://api.sahmk.sa/api/v1/market/summary/?index=TASI" \
  -H "X-API-Key: YOUR_API_KEY"

# Get top gainers
curl "https://api.sahmk.sa/api/v1/market/gainers/?limit=5&index=TASI" \
  -H "X-API-Key: YOUR_API_KEY"

# Get top by volume
curl "https://api.sahmk.sa/api/v1/market/volume/?limit=10&index=TASI" \
  -H "X-API-Key: YOUR_API_KEY"

# Get company info (tiered by plan)
curl "https://api.sahmk.sa/api/v1/company/2222/" \
  -H "X-API-Key: YOUR_API_KEY"

# Get historical data (Starter+ plan)
curl "https://api.sahmk.sa/api/v1/historical/2222/?from=2026-01-01&limit=500&offset=0" \
  -H "X-API-Key: YOUR_API_KEY"

# Get financials (Starter+ plan)
curl "https://api.sahmk.sa/api/v1/financials/2222/" \
  -H "X-API-Key: YOUR_API_KEY"

# Get dividends (Starter+ plan)
curl "https://api.sahmk.sa/api/v1/dividends/2222/" \
  -H "X-API-Key: YOUR_API_KEY"

# Get stock events (Pro+ plan)
curl "https://api.sahmk.sa/api/v1/events/?symbol=2222" \
  -H "X-API-Key: YOUR_API_KEY"
```

---

## Support

- Documentation: https://sahmk.sa/developers/docs
- Dashboard: https://sahmk.sa/developers/dashboard
- MCP Server: https://pypi.org/project/sahmk-mcp/
- Python SDK: https://pypi.org/project/sahmk/
- Contact: https://sahmk.sa/contactus?type=api-support
