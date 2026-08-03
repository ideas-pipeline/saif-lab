#!/bin/bash
# Build stocks-site/index.html from template + stocks-data.json, then git push
# Usage: bash stocks-push.sh

WORKSPACE="/srv/ideas"
DATA_FILE="$WORKSPACE/stocks-data.json"
TEMPLATE="$WORKSPACE/stocks-site/template.html"
OUTPUT="$WORKSPACE/stocks-site/index.html"

if [ ! -f "$DATA_FILE" ]; then
  echo "❌ stocks-data.json not found"
  exit 1
fi

if [ ! -f "$TEMPLATE" ]; then
  echo "❌ template.html not found"
  exit 1
fi

# (بند 6) ختم lastRunAt بكتابة ذرية قبل البناء
python3 << 'PYSTAMP'
import json, os, tempfile
from datetime import datetime, timezone, timedelta
p = "/srv/ideas/stocks-data.json"
d = json.load(open(p))
stamps = sorted({s.get('priceUpdatedAt') for s in d.get('stocks', []) if s.get('priceUpdatedAt')})
# (بند 25) الختم يشتق من جلب الأسعار لا من لحظة البناء — بناء بلا جلب لا يجدد الختم
d['lastRunAt'] = (stamps[-1] + ' الرياض') if stamps else datetime.now(timezone(timedelta(hours=3))).strftime('%Y-%m-%d %H:%M الرياض')
fd, tmp = tempfile.mkstemp(dir="/srv/ideas", suffix=".tmp")
with os.fdopen(fd, 'w') as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
os.replace(tmp, p)  # ذري — لا حالة منتصف كتابة أبداً
os.chmod(p, 0o664)  # (إصلاح) mkstemp ينشئ 600 — نعيد صلاحية المجموعة
print(f"🕐 lastRunAt: {d['lastRunAt']}")
PYSTAMP

# Read template and inject data
python3 << 'PYTHON'
import json

with open("/srv/ideas/stocks-data.json") as f:
    data = f.read()

with open("/srv/ideas/stocks-site/template.html") as f:
    template = f.read()

# Template has: const DATA = __STOCKS_DATA__;
# Replace the placeholder with actual data
output = template.replace('__STOCKS_DATA__', data, 1)

with open("/srv/ideas/stocks-site/index.html", "w") as f:
    f.write(output)

stocks_count = len(json.loads(data).get('stocks', []))
print(f"✅ Built index.html with {stocks_count} stocks")
PYTHON

# Git push
cd "$WORKSPACE/stocks-site" || exit 1
git add -A
git commit -m "update: stocks data $(date +%Y-%m-%d)" 2>/dev/null
git push origin master 2>&1

# (بند 6) فحص نشر Pages فعلياً — الدفع الناجح لا يعني نشراً ناجحاً (حدث 04-07 و05-07)
verify_pages() {
  local sha=$(git rev-parse HEAD)
  for i in $(seq 1 9); do
    sleep 10
    local res=$(curl -s "https://api.github.com/repos/ideas-pipeline/stocks/actions/runs?per_page=1"       | python3 -c "import json,sys; r=json.load(sys.stdin)['workflow_runs'][0]; print(r['head_sha'], r['status'], r['conclusion'])" 2>/dev/null)
    local rsha=$(echo "$res" | cut -d' ' -f1)
    local status=$(echo "$res" | cut -d' ' -f2)
    local concl=$(echo "$res" | cut -d' ' -f3)
    if [ "$rsha" = "$sha" ] && [ "$status" = "completed" ]; then
      echo "$concl"; return
    fi
  done
  echo "timeout"
}

RESULT=$(verify_pages)
if [ "$RESULT" = "success" ]; then
  echo "✅ نشر Pages مؤكد"
elif [ "$RESULT" = "failure" ]; then
  echo "⚠️ نشر Pages فشل — إعادة إطلاق تلقائية (commit فارغ)"
  git commit --allow-empty -m "auto-retrigger pages deploy"
  git push origin master 2>&1
  RESULT2=$(verify_pages)
  if [ "$RESULT2" = "success" ]; then
    echo "✅ نشر Pages نجح بعد إعادة الإطلاق"
  else
    echo "❌ نشر Pages فشل نهائياً ($RESULT2) — يتطلب تدخلاً"
    exit 1
  fi
else
  echo "⚠️ لم يُحسم فحص النشر ($RESULT) — راجع يدوياً"
fi

echo "✅ Done"
