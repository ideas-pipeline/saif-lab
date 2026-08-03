#!/bin/bash
# Update stock price in stocks-data.json
# Usage: bash update-stock-price.sh 'اسم السهم' 22.33
# After updating all prices, run: bash stocks-push.sh

WORKSPACE="/srv/ideas"
DATA_FILE="$WORKSPACE/stocks-data.json"

STOCK_NAME="$1"
PRICE="$2"

if [ -z "$STOCK_NAME" ] || [ -z "$PRICE" ]; then
    echo "Usage: bash update-stock-price.sh 'اسم السهم' السعر"
    exit 1
fi

python3 -c "
import json, sys
from datetime import datetime, timezone, timedelta

name = sys.argv[1]
price = float(sys.argv[2])
riyadh = timezone(timedelta(hours=3))

with open('$DATA_FILE') as f:
    data = json.load(f)

found = False
for s in data['stocks']:
    if s['name'] == name:
        s['currentPrice'] = price
        found = True
        low = s.get('covidLow')
        if low:
            diff = (price - low) / low * 100
            status = '🔴 كسر القاع!' if diff < 0 else ('🟡 قريب' if diff < 10 else '🟢 فوق')
            print(f'✅ {name}: {price} ريال (قاع: {low}) → {diff:+.1f}% {status}')
        else:
            print(f'✅ {name}: {price} ريال (لا قاع متوفر)')
        break

if not found:
    print(f'❌ سهم \"{name}\" غير موجود في القاعدة')
    sys.exit(1)

data['lastUpdated'] = datetime.now(riyadh).strftime('%Y-%m-%d %H:%M الرياض')

with open('$DATA_FILE', 'w') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
" "$STOCK_NAME" "$PRICE"
