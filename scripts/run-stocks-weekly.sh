#!/bin/bash
set -e

# (حزمة الجدولة 08-07) قفل مشترك — يمنع تداخل اليومية والأسبوعية
exec 200>/srv/ideas/.pipeline.lock
flock -w 3600 200 || { echo "⛔ خط آخر يعمل — انتظرت ساعة ولم يتحرر القفل"; exit 1; }

bash /srv/ideas/scripts/fetch-weekly-technical.sh
bash /srv/ideas/scripts/fetch-sector-financials.sh
bash /srv/ideas/scripts/fetch-liquidity-debt.sh
python3 /srv/ideas/scripts/fetch-valuation-inputs.py
python3 /srv/ideas/scripts/compute-valuation.py
python3 /srv/ideas/scripts/scoring-engine.py
bash /srv/ideas/scripts/close-sma200w.sh
bash /srv/ideas/scripts/update-watchlist-accuracy.sh || echo "⚠️ accuracy فشل — نتابع النشر"
bash /srv/ideas/scripts/stocks-push.sh
