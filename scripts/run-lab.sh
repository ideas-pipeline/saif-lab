#!/bin/bash
# run-lab.sh — خط تشغيل المختبر المستقل (sahmk-direct-v3)
# =========================================================
# يجسد قيود جدولة الناقد الثلاثة (ختم 05-08ب):
#   1) مسارات صريحة في كل استدعاء (لا افتراضيات إنتاجية)
#   2) يُجدول بعد الإقفال (>15:10 الرياض) — وإلا runType=intraday فيتعطل المغذي بالتصميم
#   3) ترتيب الخط: جالب ← محرك ← مغذٍ/إغلاقات ← L1 على الملف ذاته
#
# الاستخدام:  run-lab.sh [daily|weekly|universe]
# الجدولة المقترحة (crontab — توقيت السيرفر الرياض):
#   50 16 * * 0-3  /srv/ideas/lab-mirror/scripts/run-lab.sh daily    >> /srv/ideas/lab-runs.log 2>&1
#   50 16 * * 4    /srv/ideas/lab-mirror/scripts/run-lab.sh weekly   >> /srv/ideas/lab-runs.log 2>&1
#   30 17 1 * *    /srv/ideas/lab-mirror/scripts/run-lab.sh universe >> /srv/ideas/lab-runs.log 2>&1
set -e
LAB="/srv/ideas/lab-mirror"
KEYFILE="/srv/ideas/.sahmk.key"
MODE="${1:-daily}"

# تحصين ضد التحديث الذاتي (06-08): git pull الداخلي قد يحدّث هذا الملف أثناء تنفيذه،
# وbash يقرأ السكربتات تزايدياً — لذا التنفيذ الفعلي يجري دائماً من نسخة مؤقتة تحذف نفسها.
if [ -z "$RUNLAB_EXEC_COPY" ]; then
  cp -- "$0" "$LAB/.run-lab.exec.$$"
  export RUNLAB_EXEC_COPY="$LAB/.run-lab.exec.$$"
  exec bash "$RUNLAB_EXEC_COPY" "$@"
fi
trap 'rm -f -- "$RUNLAB_EXEC_COPY"' EXIT

cd "$LAB"
exec 200>.lab.lock
flock -w 900 200 || { echo "⛔ تشغيلة أخرى قائمة — انسحاب"; exit 1; }

echo "════ run-lab [$MODE] $(date '+%Y-%m-%d %H:%M') ════"

# درس انسداد git الموثق (وملزمة ختم 04-09ج): كل مخرجات البناء المتعقَّبة تُستعاد قبل
# السحب — لا index.html وحده. classic.html صار مخرجاً يومياً بترقية 04-09، وبقاؤه
# معدَّلاً بعد بناء مات قبل الإيداع يُجهض git pull فيموت السكربت صامتاً تحت set -e.
git checkout -- index.html classic.html 2>/dev/null || true
git pull -q origin main

export SAHMK_KEY="$(cat "$KEYFILE")"
DATA="$LAB/stocks-data.json"

# ‏--watchlist-config صريح (نمط المسارات الصريحة): يغذي portfolioSymbols وإغلاقات delisted
WLCFG="$LAB/watchlist-config.json"
case "$MODE" in
  weekly)   python3 scripts/fetch-inputs-sahmk.py --data "$DATA" --weekly --watchlist-config "$WLCFG" ;;
  universe) python3 scripts/fetch-inputs-sahmk.py --data "$DATA" --maintain-universe --watchlist-config "$WLCFG"
            python3 scripts/fetch-inputs-sahmk.py --data "$DATA" --watchlist-config "$WLCFG" ;;
  divcal)   # مفكرة الويكند الخفيفة (طلب المالك 21-08): كتلتا المفكرة حصراً ثم البناء والنشر.
            # كرونا المالك المقترحان (توقيت السيرفر الرياض):
            #   20 12 * * 5  /srv/ideas/lab-mirror/scripts/run-lab.sh divcal   # الجمعة 12:20
            #   20 12 * * 6  /srv/ideas/lab-mirror/scripts/run-lab.sh divcal   # السبت 12:20
            python3 scripts/fetch-inputs-sahmk.py --data "$DATA" --divcal-only --watchlist-config "$WLCFG" ;;
  *)        python3 scripts/fetch-inputs-sahmk.py --data "$DATA" --watchlist-config "$WLCFG" ;;
esac

if [ "$MODE" = "divcal" ]; then
  # الوضع الخفيف: لا محرك ولا مغذٍ ولا إغلاقات ولا L1/digest — بناء ونشر فقط
  python3 build.py
else

python3 scripts/scoring-engine.py "$DATA"

# المغذي والإغلاقات — مسارات صريحة، ويرفضان ذاتياً أي ملف intraday/بلا ختم
STOCKS_JSON="$DATA" CONFIG_JSON="$LAB/watchlist-config.json" ARCHIVE_DIR="$LAB/archive" \
  bash scripts/feed-watchlist.sh
STOCKS_JSON="$DATA" CONFIG_JSON="$LAB/watchlist-config.json" ARCHIVE_DIR="$LAB/archive" \
  python3 scripts/close_sma200w.py

# صفحة قياس الدقة — خط المختبر هو الحاكم الوحيد لها (قرار المالك ج، موجة 07-08ب)
# تمرير خماسي صريح (درس «الملف الآخر») — فشلها يُنبه ولا يُسقط السلسلة
CONFIG_JSON="$LAB/watchlist-config.json" STOCKS_JSON="$DATA" \
  HTML_FILE="$LAB/watchlist-accuracy.html" CACHE_FILE="$LAB/.entry-adjclose-cache.json" \
  TASI_HISTORY="$LAB/tasi-history.json" \
  bash scripts/update-watchlist-accuracy.sh \
  || echo "⚠️ ALERT: update-watchlist-accuracy فشل — التشغيلة تكمل"

# الأخبار اليومية (طلب المالك 22-08 «أبغاها تتحدث دائماً») — كانت متجمدة منذ 29-07
# لأن كاتبها القديم fetch-stock-analysis.sh غير مجدول هنا. حارس داخلي يعزل الكتابة
# في news[] حصراً، وفشله يُنبه ولا يُسقط السلسلة. v2 (04-09): استعلامان لكل سهم
# (وثالث تكيّفي عند الشح) مع بوابة تخصيص وحارس خلط وترتيب زمني — ~8-12 دقيقة
python3 scripts/fetch-news.py --data "$DATA" \
  || echo "⚠️ ALERT: fetch-news فشل — التشغيلة تكمل بالأخبار القديمة"

python3 build.py
python3 scripts/self-check-L1.py "$DATA"
fi   # نهاية فرع الوضع الكامل — كتلة النشر مشتركة لكل الأوضاع

# الطبقة 2 (أسبوعي): التقرير الوصفي — فشله يُنبه ولا يُسقط السلسلة (قرار مقر 05-08ب)،
# ويسبق النشر كي يُدفع docs/weekly-digest.md مع التشغيلة
if [ "$MODE" = "weekly" ]; then
  python3 scripts/lab-digest.py --data "$DATA" \
    --config "$LAB/watchlist-config.json" --out "$LAB/docs/weekly-digest.md" \
    || echo "⚠️ ALERT: lab-digest فشل — التشغيلة تكمل"
fi

# تحقق نشر Pages (مقتبس من نمط stocks-push.sh المجرب — حادثة فشل Pages الصامت 06-08)
verify_pages() {
  local sha rsha status concl res i
  sha=$(git rev-parse HEAD)
  for i in $(seq 1 9); do
    sleep 10
    res=$(curl -s -m 20 "https://api.github.com/repos/ideas-pipeline/saif-lab/actions/runs?per_page=1" \
      | python3 -c "import json,sys; r=json.load(sys.stdin)['workflow_runs'][0]; print(r['head_sha'], r['status'], r['conclusion'])" 2>/dev/null || true)
    rsha=$(echo "$res" | cut -d' ' -f1); status=$(echo "$res" | cut -d' ' -f2); concl=$(echo "$res" | cut -d' ' -f3)
    if [ "$rsha" = "$sha" ] && [ "$status" = "completed" ]; then echo "$concl"; return; fi
  done
  echo "timeout"
}

# دفع محصّن (حادثة 04-09): دمج من جهة أخرى أثناء التشغيلة كان يرفض الدفع
# فيموت السكربت بـset -e وتبقى النتائج حبيسة الخادم. الآن: سحب بإعادة أساس ثم محاولة ثانية.
push_with_retry() {
  local i
  for i in 1 2 3; do
    if git push -q origin main 2>/dev/null; then return 0; fi
    echo "⚠️ رُفض الدفع (محاولة $i) — سحب بإعادة أساس ثم إعادة المحاولة"
    if ! git pull --rebase -q origin main; then
      git rebase --abort 2>/dev/null || true
      echo "❌ ALERT: تعارض في إعادة الأساس — تدخل يدوي مطلوب (النتائج محفوظة محلياً)"
      return 1
    fi
    sleep 3
  done
  echo "❌ ALERT: فشل الدفع بعد 3 محاولات — النتائج محفوظة محلياً بلا نشر"
  return 1
}

# النشر: إيداع ودفع نتائج التشغيلة (يغذي GitHub Pages) + تأكيد النشر
git add -A
if ! git diff --cached --quiet; then
  git -c user.email="server@saif" -c user.name="server" commit -qm "lab: تشغيلة $MODE آلية"
  if ! push_with_retry; then
    echo "════ اكتمل [$MODE] بلا نشر $(date '+%H:%M') ════"
    exit 1
  fi
  RESULT=$(verify_pages)
  if [ "$RESULT" = "success" ]; then
    echo "✅ نُشر ونشر Pages مؤكد"
  elif [ "$RESULT" = "failure" ]; then
    echo "⚠️ نشر Pages فشل — إعادة إطلاق تلقائية (إيداع فارغ)"
    git -c user.email="server@saif" -c user.name="server" commit -q --allow-empty -m "retrigger pages deploy"
    push_with_retry || true
    RESULT2=$(verify_pages)
    if [ "$RESULT2" = "success" ]; then echo "✅ نشر Pages نجح بعد إعادة الإطلاق"
    else echo "❌ ALERT: نشر Pages فشل نهائياً ($RESULT2) — تدخل يدوي"; fi
  else
    echo "⚠️ لم يُحسم فحص Pages ($RESULT) — راجع يدوياً"
  fi
else
  echo "ℹ️ لا تغييرات للنشر"
fi
echo "════ اكتمل [$MODE] $(date '+%H:%M') ════"
