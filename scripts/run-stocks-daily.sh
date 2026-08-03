#!/bin/bash
set -e

# (حزمة الجدولة 08-07) قفل مشترك — يمنع تداخل اليومية والأسبوعية
exec 200>/srv/ideas/.pipeline.lock
flock -w 3600 200 || { echo "⛔ خط آخر يعمل — انتظرت ساعة ولم يتحرر القفل"; exit 1; }

# (بند 6) تنبيه الفشل: ملف حالة + تيليجرام إن وُجد ملف الإعداد
STATUS_FILE="/srv/ideas/pipeline-status.json"
notify_fail() {
  local step="$1"
  printf '{"status":"failed","step":"%s","at":"%s"}\n' "$step" "$(date '+%Y-%m-%d %H:%M:%S')" > "$STATUS_FILE"
  # /root/.telegram-alert: سطران — التوكن ثم chat_id (600 root فقط)
  if [ -r /root/.telegram-alert ]; then
    local TOKEN=$(sed -n 1p /root/.telegram-alert)
    local CHAT=$(sed -n 2p /root/.telegram-alert)
    curl -s -m 10 "https://api.telegram.org/bot${TOKEN}/sendMessage" \
      --data-urlencode "chat_id=${CHAT}" \
      --data-urlencode "text=🔴 سيف تداول: فشل الخط اليومي عند: ${step} — $(date '+%H:%M')" > /dev/null || true
  fi
}
trap 'notify_fail "$BASH_COMMAND"' ERR

bash /srv/ideas/scripts/fetch-stock-prices.sh
bash /srv/ideas/scripts/fetch-stock-analysis.sh
bash /srv/ideas/scripts/update-financials.sh
python3 /srv/ideas/scripts/compute-valuation.py
bash /srv/ideas/scripts/fetch-daily-extra.sh /srv/ideas/stocks-data.json
python3 /srv/ideas/scripts/scoring-engine.py
bash /srv/ideas/scripts/feed-watchlist.sh
bash /srv/ideas/scripts/update-watchlist-accuracy.sh
python3 /srv/ideas/scripts/self-check-L1.py
bash /srv/ideas/scripts/stocks-push.sh

# (بند 6) نجاح كامل: ملف الحالة + نسخة مستقرة ذرية للقطة 16:45
printf '{"status":"ok","at":"%s"}\n' "$(date '+%Y-%m-%d %H:%M:%S')" > "$STATUS_FILE"
cp /srv/ideas/stocks-data.json /srv/ideas/stocks-data-stable.json.tmp
mv /srv/ideas/stocks-data-stable.json.tmp /srv/ideas/stocks-data-stable.json
chmod 664 /srv/ideas/stocks-data-stable.json
