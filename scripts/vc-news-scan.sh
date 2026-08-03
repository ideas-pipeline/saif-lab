#!/bin/bash
# سحب أخبار الاستثمار الجريء السعودي الأسبوعي
# يبحث عن جولات تمويل جديدة ويحدّث vc-data.json
# Usage: bash vc-news-scan.sh

WORKSPACE="/srv/ideas"
DATA_FILE="$WORKSPACE/saif-invest/data/vc-data.json"
SITE_DIR="$WORKSPACE/saif-invest"

echo "🔍 بحث عن أخبار الاستثمار الجريء السعودي..."
echo "$(date '+%Y-%m-%d %H:%M:%S')"

python3 << 'PYTHON'
import json, urllib.request, urllib.parse, re
from datetime import datetime, timezone, timedelta

WORKSPACE = "/srv/ideas"
DATA_FILE = f"{WORKSPACE}/saif-invest/data/vc-data.json"

with open(DATA_FILE) as f:
    data = json.load(f)

existing_companies = {c['nameEn'].lower() for c in data['companies']}
new_insights = []

# Search sources for Saudi VC news
search_queries = [
    "Saudi startup funding round 2026",
    "Saudi venture capital investment 2026", 
    "تمويل شركات ناشئة سعودية 2026",
    "جولة استثمارية السعودية 2026"
]

headers = {"User-Agent": "Mozilla/5.0"}

for query in search_queries:
    try:
        url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=ar&gl=SA&ceid=SA:ar"
        req = urllib.request.Request(url, headers=headers)
        resp = urllib.request.urlopen(req, timeout=10)
        content = resp.read().decode('utf-8', errors='ignore')
        
        # Parse RSS items
        items = re.findall(r'<item>(.*?)</item>', content, re.DOTALL)
        for item in items[:5]:
            title = re.search(r'<title>(.*?)</title>', item)
            link = re.search(r'<link>(.*?)</link>', item)
            pubDate = re.search(r'<pubDate>(.*?)</pubDate>', item)
            
            if title:
                new_insights.append({
                    "title": title.group(1).replace('<![CDATA[','').replace(']]>','').strip(),
                    "url": link.group(1).strip() if link else "",
                    "date": pubDate.group(1).strip() if pubDate else "",
                    "query": query
                })
    except Exception as e:
        print(f"  ⚠️ خطأ في البحث: {query[:30]}... — {e}")

# Deduplicate by title
seen = set()
unique = []
for item in new_insights:
    key = item['title'][:50]
    if key not in seen:
        seen.add(key)
        unique.append(item)

print(f"\n📰 تم العثور على {len(unique)} خبر")

# Save results for the agent to review
output = {
    "scanDate": datetime.now(timezone(timedelta(hours=3))).strftime('%Y-%m-%d %H:%M'),
    "totalResults": len(unique),
    "items": unique[:20]
}

with open(f"{WORKSPACE}/saif-invest/data/weekly-scan.json", 'w') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"💾 تم الحفظ في weekly-scan.json")

# Print top items
for i, item in enumerate(unique[:10], 1):
    print(f"  {i}. {item['title'][:80]}")

PYTHON

echo ""
echo "✅ انتهى البحث الأسبوعي"
