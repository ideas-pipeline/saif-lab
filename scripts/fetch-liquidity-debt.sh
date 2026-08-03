#!/bin/bash
# Fetch liquidity (turnover ratio) + debt health for all stocks
# Adds: liquidityScore{}, debtHealth{} to each stock in stocks-data.json
# Usage: bash fetch-liquidity-debt.sh
# NO agent needed — pure bash + python

WORKSPACE="/srv/ideas"
DATA_FILE="$WORKSPACE/stocks-data.json"

echo "💰🔄 جلب بيانات السيولة والديون..."
echo "$(date '+%Y-%m-%d %H:%M:%S')"

/usr/bin/python3 << 'PYTHON'
import json, time, sys

try:
    import yfinance as yf
except ImportError:
    print("ERROR: yfinance not installed. Run: pip3 install yfinance")
    sys.exit(1)

with open('/srv/ideas/stocks-data.json') as f:
    data = json.load(f)

stocks = data['stocks']
updated = 0
errors = 0
total = len(stocks)

def safe_num(val):
    if val is None:
        return None
    try:
        f = float(val)
        if str(f) == 'nan' or str(f) == 'inf':
            return None
        return f
    except:
        return None

def get_turnover_color(ratio):
    if ratio is None:
        return 'gray', 'غير متوفر'
    if ratio >= 0.5:
        return 'green', 'سيولة عالية'
    elif ratio >= 0.1:
        return 'yellow', 'سيولة متوسطة'
    else:
        return 'red', 'سيولة ضعيفة'

def get_debt_color(net_debt_ebitda, is_bank=False):
    if net_debt_ebitda is None:
        return 'gray', 'غير متوفر'
    if net_debt_ebitda < 0:
        return 'green', 'فوائض نقدية'
    elif net_debt_ebitda <= 1:
        return 'green', 'دين مريح'
    elif net_debt_ebitda <= 3:
        return 'yellow', 'دين معقول'
    else:
        return 'red', 'دين مرتفع'

def get_bank_color(cost_to_income):
    if cost_to_income is None:
        return 'gray', 'غير متوفر'
    if cost_to_income < 35:
        return 'green', 'كفاءة ممتازة'
    elif cost_to_income < 45:
        return 'yellow', 'كفاءة مقبولة'
    else:
        return 'red', 'كفاءة ضعيفة'

for i, stock in enumerate(stocks):
    sym = stock.get('symbol', '')
    if not sym:
        continue

    try:
        ticker = yf.Ticker(f'{sym}.SR')
        info = ticker.info or {}
        
        # === 1. TURNOVER RATIO ===
        avg_vol = safe_num(info.get('averageVolume'))
        shares_out = safe_num(info.get('sharesOutstanding'))
        
        turnover = None
        if avg_vol and shares_out and shares_out > 0:
            turnover = round((avg_vol / shares_out) * 100, 3)
        
        t_color, t_label = get_turnover_color(turnover)
        
        stock['liquidityScore'] = {
            'avgVolume20d': int(avg_vol) if avg_vol else None,
            'sharesOutstanding': int(shares_out) if shares_out else None,
            'turnoverPct': turnover,
            'color': t_color,
            'label': t_label
        }
        
        # === 2. DEBT HEALTH ===
        is_bank = stock.get('sector') == 'Financials' and 'Bank' in stock.get('industry', '')
        
        if is_bank:
            # Banks: use Cost-to-Income
            try:
                inc = ticker.income_stmt
                if inc is not None and not inc.empty:
                    total_rev = safe_num(inc.iloc[:, 0].get('Total Revenue'))
                    operating_exp = safe_num(inc.iloc[:, 0].get('Operating Expense'))
                    
                    cti = None
                    if total_rev and operating_exp and total_rev > 0:
                        cti = round((operating_exp / total_rev) * 100, 1)
                    
                    d_color, d_label = get_bank_color(cti)
                    
                    stock['debtHealth'] = {
                        'type': 'bank',
                        'costToIncome': cti,
                        'color': d_color,
                        'label': d_label
                    }
                else:
                    stock['debtHealth'] = {'type': 'bank', 'color': 'gray', 'label': 'غير متوفر'}
            except:
                stock['debtHealth'] = {'type': 'bank', 'color': 'gray', 'label': 'غير متوفر'}
        else:
            # Non-banks: Net Debt / EBITDA
            total_debt = safe_num(info.get('totalDebt'))
            total_cash = safe_num(info.get('totalCash'))
            ebitda = safe_num(info.get('ebitda'))
            
            net_debt = None
            net_debt_ebitda = None
            
            if total_debt is not None and total_cash is not None:
                net_debt = total_debt - total_cash
            
            if net_debt is not None and ebitda and ebitda > 0:
                net_debt_ebitda = round(net_debt / ebitda, 1)
            
            d_color, d_label = get_debt_color(net_debt_ebitda)
            
            stock['debtHealth'] = {
                'type': 'company',
                'totalDebt': int(total_debt) if total_debt else None,
                'totalCash': int(total_cash) if total_cash else None,
                'netDebt': int(net_debt) if net_debt is not None else None,
                'ebitda': int(ebitda) if ebitda else None,
                'netDebtToEbitda': net_debt_ebitda,
                'color': d_color,
                'label': d_label
            }
        
        updated += 1
        status = f"✅ T:{t_color[0]} D:{d_color[0] if 'debtHealth' in stock else '?'}"
        
    except Exception as e:
        errors += 1
        status = f"❌ {str(e)[:30]}"
    
    if (i+1) % 25 == 0:
        print(f"  [{i+1}/{total}] تم {updated} | أخطاء {errors}")
    
    time.sleep(0.5)

# Save
from datetime import datetime, timezone, timedelta
riyadh = timezone(timedelta(hours=3))
data['liquidityDebtUpdated'] = datetime.now(riyadh).strftime('%Y-%m-%d %H:%M الرياض')

with open('/srv/ideas/stocks-data.json', 'w') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

# Summary
green_t = sum(1 for s in stocks if s.get('liquidityScore', {}).get('color') == 'green')
yellow_t = sum(1 for s in stocks if s.get('liquidityScore', {}).get('color') == 'yellow')
red_t = sum(1 for s in stocks if s.get('liquidityScore', {}).get('color') == 'red')

green_d = sum(1 for s in stocks if s.get('debtHealth', {}).get('color') == 'green')
yellow_d = sum(1 for s in stocks if s.get('debtHealth', {}).get('color') == 'yellow')
red_d = sum(1 for s in stocks if s.get('debtHealth', {}).get('color') == 'red')

print(f"\n{'='*50}")
print(f"✅ تم تحديث {updated}/{total} سهم")
print(f"❌ أخطاء: {errors}")
print(f"\n🔄 السيولة: 🟢{green_t} 🟡{yellow_t} 🔴{red_t}")
print(f"💰 الديون:  🟢{green_d} 🟡{yellow_d} 🔴{red_d}")
PYTHON

# (إصلاح بند 6) أُزيل النشر الهجين (كان ينشر ديوناً جديدة بنقاط قديمة)

echo ""
echo "✅ تم تحديث السيولة والديون"
echo "$(date '+%Y-%m-%d %H:%M:%S')"
