#!/bin/bash
# Fetch current stock prices and update stocks-data.json
# Usage: bash fetch-stocks.sh
# Uses web_search results parsed by the calling agent (GPT-4.1)
# This script shows the current state for the agent to build the report

WORKSPACE="/srv/ideas"
DATA_FILE="$WORKSPACE/stocks-data.json"

if [ ! -f "$DATA_FILE" ]; then
    echo "ERROR: stocks-data.json not found"
    exit 1
fi

python3 -c "
import json
from datetime import datetime, timezone, timedelta

with open('$DATA_FILE') as f:
    data = json.load(f)

portfolio = data.get('portfolio', [])
stocks = data.get('stocks', [])

print('🟢 محفظتك:')
for s in stocks:
    if s['name'] in portfolio:
        price = s.get('currentPrice')
        low = s.get('covidLow')
        if price and low:
            diff = (price - low) / low * 100
            status = '🔴 كسر القاع!' if diff < 0 else ('🟡 قريب' if diff < 10 else '🟢 فوق القاع')
            print(f'  • {s[\"name\"]}: {price} ريال (قاع: {low}) → {diff:+.1f}% {status}')
        else:
            print(f'  • {s[\"name\"]}: السعر الحالي: {price or \"غير متوفر\"} | قاع: {low or \"غير متوفر\"}')

print()
print('🔴 أسهم كسرت قاع كورونا:')
broken = 0
for s in stocks:
    price = s.get('currentPrice')
    low = s.get('covidLow')
    if price and low and price < low:
        diff = (price - low) / low * 100
        tag = ' ⭐ محفظتي' if s['name'] in portfolio else ''
        print(f'  • {s[\"name\"]}: {price} ريال (قاع: {low}) → {diff:.1f}%{tag}')
        broken += 1
if broken == 0:
    print('  لا توجد أسهم كسرت القاع حالياً ✅')

print()
print('🟡 أسهم قريبة من القاع (أقل من 10%):')
near = 0
for s in stocks:
    price = s.get('currentPrice')
    low = s.get('covidLow')
    if price and low and price >= low:
        diff = (price - low) / low * 100
        if diff < 10:
            tag = ' ⭐ محفظتي' if s['name'] in portfolio else ''
            print(f'  • {s[\"name\"]}: {price} ريال (قاع: {low}) → +{diff:.1f}%{tag}')
            near += 1
if near == 0:
    print('  لا توجد أسهم قريبة من القاع')

print(f'\nآخر تحديث: {data.get(\"lastUpdated\", \"لم يتحدث\")}')
print(f'إجمالي الأسهم المراقبة: {len(stocks)}')
"
