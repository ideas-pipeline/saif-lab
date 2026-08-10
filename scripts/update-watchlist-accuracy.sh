#!/bin/bash
# update-watchlist-accuracy.sh — v3 (إعادة التبيئة لخط المختبر الحاكم، موجة 07-08ب)
# ---
# المصدر الوحيد للتحكم: watchlist-config.json (يُمرر صراحة)
# سلسلة سعر الدخول: sahmk-close → cache → manual-fallback (سقطت Yahoo نهائياً —
#   قرار sahmk-حصراً المختوم؛ entrySource يمر للصفحة والشارة ⚠️ على الواجهة)
# النطاق: api.sahmk.sa بنمط الجالب المعتمد | المفتاح: SAHMK_KEY من البيئة أو
#   SAHMK_KEYFILE — قراءة كسولة عند أول استدعاء لا عند تحميل الوحدة
# حارس close-only: runType غير close في STOCKS_JSON → تخطٍ بطباعة (نمط المغذي)
# الكتابة ذرية (tmp + os.replace) | لا افتراضيات إنتاجية: الافتراضيات نسبية
#   لجذر المستودع (أبو مجلد السكربت)، والتمرير الصريح هو المعتمد في run-lab.sh

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG_JSON="${CONFIG_JSON:-$REPO_ROOT/watchlist-config.json}"
STOCKS_JSON="${STOCKS_JSON:-$REPO_ROOT/stocks-data.json}"
HTML_FILE="${HTML_FILE:-$REPO_ROOT/watchlist-accuracy.html}"
CACHE_FILE="${CACHE_FILE:-$REPO_ROOT/.entry-adjclose-cache.json}"
TASI_HISTORY="${TASI_HISTORY:-$REPO_ROOT/tasi-history.json}"

export CONFIG_JSON STOCKS_JSON HTML_FILE CACHE_FILE TASI_HISTORY

python3 << 'PYEOF'
import json, re, os, time, urllib.request
from datetime import datetime, timedelta

CONFIG_JSON = os.environ["CONFIG_JSON"]
STOCKS_JSON = os.environ["STOCKS_JSON"]
HTML_FILE   = os.environ["HTML_FILE"]
CACHE_FILE  = os.environ["CACHE_FILE"]

with open(STOCKS_JSON) as f:
    data = json.load(f)

# ── حارس close-only (شرط المحلل 2 معمماً): صفحة الدقة لا تُولّد من ملف سوق مفتوح ──
_rt = data.get("runType")
if _rt != "close":
    print(f"⛔ update-watchlist-accuracy: تشغيلة سوق مفتوح (runType={_rt}) — "
          "لا تحديث للصفحة، أرقام الدقة بأسعار إقفال حصراً")
    raise SystemExit(0)

# ── المفتاح: كسول — يُقرأ عند أول حاجة فعلية للشبكة، وغيابه يهبط للسلسلة الاحتياطية ──
BASE = "https://api.sahmk.sa/api/v1"
_key_cache = {"read": False, "key": None}

def sahmk_key():
    if not _key_cache["read"]:
        _key_cache["read"] = True
        k = os.environ.get("SAHMK_KEY", "")
        kf = os.environ.get("SAHMK_KEYFILE", "")
        if not k and kf and os.path.exists(kf):
            k = open(kf).read().strip()
        _key_cache["key"] = k or None
        if not k:
            print("  ℹ️ لا مفتاح SAHMK (بيئة/SAHMK_KEYFILE) — سلسلة cache/manual فقط")
    return _key_cache["key"]

def _sahmk_get(url):
    key = sahmk_key()
    if not key:
        return None
    req = urllib.request.Request(url, headers={"X-API-Key": key, "User-Agent": "Mozilla/5.0"})
    for attempt in range(2):
        try:
            return json.load(urllib.request.urlopen(req, timeout=20))
        except Exception:
            if attempt == 0:
                time.sleep(2)
    return None

def fetch_sahmk_entry_close(symbol, entry_date):
    """إغلاق يوم الدخول (أول جلسة ≥ التاريخ) من سهمك — نافذة 12 يوماً"""
    end = (datetime.strptime(entry_date, "%Y-%m-%d") + timedelta(days=12)).strftime("%Y-%m-%d")
    r = _sahmk_get(f"{BASE}/historical/{symbol}/?from={entry_date}&to={end}")
    if r is None:
        return None, None
    rows = r if isinstance(r, list) else r.get("data", [])
    for row in sorted(rows, key=lambda x: x.get("date", "")):
        if row.get("date", "") >= entry_date and row.get("close"):
            return round(row["close"], 2), row["date"]
    return None, None

def fetch_sahmk_divs_since(symbol, entry_date, until):
    """مجموع التوزيعات النقدية التي تاريخ أحقيتها بين الدخول والنهاية"""
    r = _sahmk_get(f"{BASE}/dividends/{symbol}/?limit=50")
    if r is None:
        return None
    tot = 0.0
    for h in r.get("history", []):
        ed = h.get("eligibility_date") or ""
        if ed and entry_date <= ed <= until and h.get("value"):
            tot += h["value"]
    return round(tot, 3)

# ── 1) قراءة config + الأسعار + الـ cache ──
with open(CONFIG_JSON) as f:
    config = json.load(f)
stocks_config = config.get("stocks", [])

price_map = {s["symbol"]: s.get("currentPrice") for s in data.get("stocks", [])}

# ── 1-ب) measurement v3 (2026-08-03): عائد تاسي للفترة المطابقة لكل مدخل ──
# قيمة تاسي عند تاريخ d = إغلاق آخر سجل تاريخه <= d (عطل/نهايات أسبوع = آخر إغلاق متاح).
# نهاية فترة المفتوحة = يوم آخر تحديث بيانات (lastUpdated) لا «اليوم» الميلادي.
# entryDate أقدم من أول سجل → tasiRet=null (لا تقدير ولا استيفاء — منع الدقة الزائفة).
TASI_HISTORY = os.environ["TASI_HISTORY"]
with open(TASI_HISTORY) as f:
    _tasi_rows = sorted((h["date"], h["close"]) for h in json.load(f)["data"] if h.get("close"))

def tasi_close_at(d):
    prev = None
    for td, tc in _tasi_rows:
        if td <= d:
            prev = tc
        else:
            break
    return prev

_lu_day = str(data.get("lastUpdated", ""))[:10]

def tasi_period(entry_date, end_date):
    """يعيد (tasiRet%, periodDays) أو (None, None/أيام)"""
    if not entry_date:
        return None, None
    end = end_date or _lu_day
    try:
        days = (datetime.strptime(end, "%Y-%m-%d") - datetime.strptime(entry_date, "%Y-%m-%d")).days
    except ValueError:
        return None, None
    if _tasi_rows and entry_date < _tasi_rows[0][0]:
        return None, days
    s0, s1 = tasi_close_at(entry_date), tasi_close_at(end)
    if not s0 or not s1:
        return None, days
    return round((s1 - s0) / s0 * 100, 2), days

cache = {}
if os.path.exists(CACHE_FILE):
    try:
        with open(CACHE_FILE) as f:
            cache = json.load(f)
    except Exception:
        cache = {}

today   = datetime.now().strftime("%Y-%m-%d")
now_iso = datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")
now_iso = now_iso[:-2] + ":" + now_iso[-2:]

# ── 2) بناء كتلة WATCHLIST ──
lines = ["const WATCHLIST = ["]
stats = {"sahmk-close": 0, "cache": 0, "manual-fallback": 0, "same-day-close": 0}
for s in stocks_config:
    symbol      = s["symbol"]
    display_sym = symbol          # بلا لاحقة .SR — أثر حقبة Yahoo أزيل (موجة 07-08ب)
    name        = s["name"]
    sector      = s.get("sector", "")
    stype       = s.get("type", "buy")
    manual      = s["entryPrice"]
    entry_date  = s.get("entryDate", config.get("entryDate", ""))
    track       = s.get("track", "")
    category    = s.get("category", "")
    current     = price_map.get(symbol)
    status      = s.get("status", "open")
    close_date  = s.get("closeDate", "")
    close_price = s.get("closePrice")
    close_reason = s.get("closeReason", "")
    div_until   = close_date if (status == "closed" and close_date) else today

    # سلسلة سعر الدخول: sahmk-close → cache → manual-fallback (لا Yahoo)
    entry_price, source, divs = manual, "manual-fallback", 0
    if entry_date == today and current is not None:
        entry_price, source = current, "same-day-close"
    elif entry_date:
        key = f"{symbol}|{entry_date}"
        skey = "S|" + key
        _c = cache.get(skey)
        sc = _c.get("close") if isinstance(_c, dict) else None
        sc_from_cache = sc is not None
        if sc is None:
            sc, sday = fetch_sahmk_entry_close(symbol, entry_date)
            if sc is not None:
                time.sleep(0.4)
                cache[skey] = {"close": sc, "tradingDay": sday, "fetchedAt": today}
        if sc is not None:
            entry_price = sc
            source = "cache" if sc_from_cache else "sahmk-close"
            dkey = "D|" + key + "|" + div_until
            if dkey in cache:
                divs = cache[dkey]
            else:
                d = fetch_sahmk_divs_since(symbol, entry_date, div_until)
                if d is not None:
                    time.sleep(0.4)
                    divs = d
                    if status == "closed":     # فترة المغلقة ثابتة — توزيعاتها تُثبت
                        cache[dkey] = d
                else:
                    divs = 0
        elif key in cache and isinstance(cache[key], dict) and cache[key].get("adj") is not None:
            # بقايا كاش الحقبة السابقة (adjclose): تُقبل موسومة cache — بلا توزيعات
            # (القيمة معدلة للتوزيعات أصلاً — جمعها مع divsSince ازدواج)
            entry_price, source, divs = cache[key]["adj"], "cache", 0
    stats[source] += 1

    mark = {"sahmk-close": "🟢", "cache": "🔁", "manual-fallback": "⚠️", "same-day-close": "🆕"}[source]
    print(f"  {mark} {symbol} entry: {entry_price} ({source}, يدوي: {manual})")

    if current is not None:
        price_str = f"{current},           // ✅ confirmed {today}"
    else:
        price_str = "null,              // ⚠️ not found in stocks-data.json"
        print(f"  ⚠️  {symbol} → currentPrice not found")

    lines.append("  {")
    lines.append(f'    symbol:        "{display_sym}",')
    lines.append(f'    name:          "{name}",')
    lines.append(f'    sector:        "{sector}",')
    lines.append(f'    type:          "{stype}",          // "buy" | "sell"')
    lines.append(f'    entryPrice:    {entry_price},      // {source} | يدوي أصلي: {manual}')
    lines.append(f'    entrySource:   "{source}",         // manual-fallback → شارة ⚠️ على الصفحة (عرضها شأن الواجهة)')
    lines.append(f"    divsSince:     {divs},")
    # measurement v3: عائد تاسي للفترة المطابقة + طول الفترة بالأيام + نظام السوق عند الدخول
    _end = close_date if (status == "closed" and close_date) else None
    _tret, _tdays = tasi_period(entry_date, _end)
    lines.append(f"    tasiRet:       {_tret if _tret is not None else 'null'},")
    lines.append(f"    periodDays:    {_tdays if _tdays is not None else 'null'},")
    lines.append(f'    regimeAtEntry: "{s.get("regimeAtEntry", "")}",')
    if status == "closed":
        lines.append(f"    status:        \"closed\",")
        lines.append(f"    closeDate:     \"{close_date}\",")
        cp2 = close_price if close_price is not None else "null"
        lines.append(f"    closePrice:    {cp2},")
        lines.append(f"    closeReason:   \"{close_reason}\",")
    if entry_date:
        lines.append(f'    entryDate:     "{entry_date}",')
    if track:
        lines.append(f'    track:         "{track}",')
    if category:
        lines.append(f'    category:      "{category}",')
    # عينة الظل الثانية (قيمة-تحت-الفلتر): أختامها البحثية تمر للصفحة
    if s.get("sampleType"):
        lines.append(f'    sampleType:    "{s["sampleType"]}",')
        for jk in ("maePct", "peAtEntry", "peSectorMedianAtEntry", "priceVsSmaPct", "qualityAtEntry", "excessNet"):
            if s.get(jk) is not None:
                lines.append(f"    {jk}: {s[jk]},")
        if s.get("filterCrossDate"):
            lines.append(f'    filterCrossDate: "{s["filterCrossDate"]}",')
            lines.append(f"    filterCrossPrice: {s.get('filterCrossPrice')},")
    elif s.get("maePct") is not None:   # ‏MAE للمطبقة والظل (موجة 07-08ب)
        lines.append(f"    maePct: {s['maePct']},")
    lines.append(f"    currentPrice:  {price_str}")
    lines.append("  },")
lines.append("];")
new_block = "\n".join(lines)

# ── 3) حفظ الـ cache (ذرياً) ──
tmp = CACHE_FILE + ".tmp"
with open(tmp, "w") as f:
    json.dump(cache, f, ensure_ascii=False, indent=1)
os.replace(tmp, CACHE_FILE)

# ── 4) استبدال الكتلة في الـ HTML — كتابة ذرية ──
with open(HTML_FILE) as f:
    html = f.read()
new_html, count = re.subn(r"const WATCHLIST = \[.*?\];", new_block, html, flags=re.DOTALL)
if count != 1:
    print(f"❌ WATCHLIST block not found or multiple matches ({count}) — aborting")
    raise SystemExit(1)
# ‏updatedAt = ختم توليد الصفحة الآلي (كان التعليق القديم «تحديث يدوي» أثراً مضللاً)
new_html = re.sub(r'(updatedAt:\s*")[^"]+(")', r"\g<1>" + now_iso + r"\2", new_html)
new_html = new_html.replace('// آخر تحديث يدوي للأسعار', '// ختم توليد الصفحة الآلي (خط المختبر)')
# حذف تعليق updatePrices الميت توليدياً — يوثق عقد isSuccess القديم ولاحقة .SR المنسوختين
# (الصفحة ملك وكيل الواجهة — الحذف يتم هنا عند الحقن لا بتعديل يدوي متوازٍ)
new_html = re.sub(r"/\*\s*\n\s*═+\s*\n\s*🔌 JSON UPDATE HOOK.*?\*/\s*\n", "", new_html, flags=re.DOTALL)

tmp_html = HTML_FILE + ".tmp"
with open(tmp_html, "w") as f:
    f.write(new_html)
os.replace(tmp_html, HTML_FILE)

_t_ok = sum(1 for s in stocks_config if tasi_period(s.get("entryDate", config.get("entryDate", "")), s.get("closeDate") if s.get("status") == "closed" else None)[0] is not None)
print(f"\n✅ Done v3 lab-line — {len(stocks_config)} stocks | sahmk: {stats['sahmk-close']} | cache: {stats['cache']} | fallback: {stats['manual-fallback']} | same-day: {stats['same-day-close']} | tasiRet: {_t_ok}/{len(stocks_config)}")
PYEOF

if [ $? -ne 0 ]; then
    echo "⚠️ ALERT: update-watchlist-accuracy فشل — السلسلة تكمل"
fi
