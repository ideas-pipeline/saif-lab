#!/bin/bash
# v2 (2026-07-20): SAHMK bulk primary (5 دفعات x50) + Yahoo fallback صامت لكل رمز مفقود
# وسم نسخة المعايير: sahmk-bulk-v1 (data.priceSource + priceSourceSince في stocks-data.json)
# العقد كما هو: currentPrice, previousClose, dailyChange, priceUpdatedAt, lastUpdated
# النسخة السابقة: archive/fetch-stock-prices.sh.pre-sahmk-2026-07-20

python3 /srv/ideas/scripts/fetch_prices_v2.py

# Show summary
bash /srv/ideas/scripts/fetch-stocks.sh

# (بند 6) لا نشر مبكر — النشر الوحيد نهاية run-stocks-daily.sh
