#!/bin/bash
# جلب البيانات المالية المتخصصة لكل قطاع (بنوك + تأمين)
# يضيف sectorFinancials{} لكل سهم في stocks-data.json
# Usage: bash fetch-sector-financials.sh [--dry-run]

WORKSPACE="/srv/ideas"
DATA_FILE="$WORKSPACE/stocks-data.json"
DRY_RUN="${1:-}"

echo "🏦🛡️ جلب البيانات المالية المتخصصة (بنوك + تأمين)..."
echo "$(date '+%Y-%m-%d %H:%M:%S')"

/usr/bin/python3 << 'PYTHON'
import json, sys, time

# Lazy import to handle missing yfinance gracefully
try:
    import yfinance as yf
except ImportError:
    print("ERROR: yfinance not installed")
    sys.exit(1)

DRY_RUN = "--dry-run" in sys.argv

with open('/srv/ideas/stocks-data.json') as f:
    data = json.load(f)

stocks = data['stocks']

def safe_float(val):
    """Convert to float safely"""
    if val is None:
        return 0
    try:
        f = float(val)
        if str(f) == 'nan':
            return 0
        return f
    except:
        return 0

def fetch_bank_metrics(symbol):
    """جلب مؤشرات البنوك المتخصصة"""
    try:
        stock = yf.Ticker(f'{symbol}.SR')
        inc = stock.income_stmt
        bs = stock.balance_sheet
        
        metrics = {'type': 'bank', 'source': 'Yahoo Finance'}
        
        if inc is not None and not inc.empty:
            latest = inc.iloc[:, 0]
            metrics['totalRevenue'] = safe_float(latest.get('Total Revenue'))
            metrics['operatingExpense'] = safe_float(latest.get('Operating Expense'))
            metrics['netIncome'] = safe_float(latest.get('Net Income'))
            metrics['sga'] = safe_float(latest.get('General And Administrative Expense'))
            metrics['depreciation'] = safe_float(latest.get('Depreciation And Amortization In Income Statement'))
            metrics['taxProvision'] = safe_float(latest.get('Tax Provision'))
            metrics['pretaxIncome'] = safe_float(latest.get('Pretax Income'))
        
        if bs is not None and not bs.empty:
            latest_bs = bs.iloc[:, 0]
            metrics['totalAssets'] = safe_float(latest_bs.get('Total Assets'))
            metrics['equity'] = safe_float(latest_bs.get('Stockholders Equity'))
            metrics['totalDebt'] = safe_float(latest_bs.get('Total Debt'))
            metrics['cashEquivalents'] = safe_float(latest_bs.get('Cash And Cash Equivalents'))
            metrics['investments'] = safe_float(latest_bs.get('Investmentin Financial Assets'))
        
        # Calculate derived metrics
        if metrics.get('totalAssets') and metrics.get('netIncome'):
            metrics['ROA'] = round(metrics['netIncome'] / metrics['totalAssets'] * 100, 2)
        
        if metrics.get('totalRevenue') and metrics.get('operatingExpense'):
            metrics['costToIncome'] = round(metrics['operatingExpense'] / metrics['totalRevenue'] * 100, 1)
            # Efficiency ratio (same concept, includes depreciation)
            total_opex = metrics['operatingExpense']
            metrics['efficiencyRatio'] = round(total_opex / metrics['totalRevenue'] * 100, 1)
        
        if metrics.get('equity') and metrics.get('netIncome'):
            metrics['ROE_calc'] = round(metrics['netIncome'] / metrics['equity'] * 100, 2)
        
        metrics['updatedAt'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        return metrics
        
    except Exception as e:
        return {'type': 'bank', 'error': str(e)}


def fetch_insurance_metrics(symbol):
    """جلب مؤشرات التأمين المتخصصة"""
    try:
        stock = yf.Ticker(f'{symbol}.SR')
        inc = stock.income_stmt
        bs = stock.balance_sheet
        
        metrics = {'type': 'insurance', 'source': 'Yahoo Finance'}
        
        if inc is not None and not inc.empty:
            latest = inc.iloc[:, 0]
            metrics['totalRevenue'] = safe_float(latest.get('Total Revenue'))
            metrics['claims'] = safe_float(latest.get('Net Policyholder Benefits And Claims'))
            metrics['totalExpenses'] = safe_float(latest.get('Total Expenses'))
            metrics['operatingExpense'] = safe_float(latest.get('Operating Expense'))
            metrics['netIncome'] = safe_float(latest.get('Net Income'))
            metrics['sga'] = safe_float(latest.get('Selling General And Administration'))
        
        if bs is not None and not bs.empty:
            latest_bs = bs.iloc[:, 0]
            metrics['totalAssets'] = safe_float(latest_bs.get('Total Assets'))
            metrics['equity'] = safe_float(latest_bs.get('Stockholders Equity'))
            metrics['investments'] = safe_float(latest_bs.get('Investmentin Financial Assets'))
        
        # Calculate derived metrics
        rev = metrics.get('totalRevenue', 0)
        claims = metrics.get('claims', 0)
        total_exp = metrics.get('totalExpenses', 0)
        
        if rev and claims:
            metrics['lossRatio'] = round(claims / rev * 100, 1)
        
        if rev and total_exp:
            non_claim_expense = total_exp - claims
            metrics['expenseRatio'] = round(non_claim_expense / rev * 100, 1) if rev else 0
            metrics['combinedRatio'] = round(
                metrics.get('lossRatio', 0) + metrics.get('expenseRatio', 0), 1
            )
        
        if metrics.get('totalAssets') and metrics.get('netIncome'):
            metrics['ROA'] = round(metrics['netIncome'] / metrics['totalAssets'] * 100, 2)
        
        if metrics.get('equity') and metrics.get('netIncome'):
            metrics['ROE_calc'] = round(metrics['netIncome'] / metrics['equity'] * 100, 2)
        
        # Investment yield (if investment data available)
        if metrics.get('investments') and metrics.get('totalAssets'):
            metrics['investmentRatio'] = round(metrics['investments'] / metrics['totalAssets'] * 100, 1)
        
        metrics['updatedAt'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        return metrics
        
    except Exception as e:
        return {'type': 'insurance', 'error': str(e)}


# Process stocks
bank_count = 0
insurance_count = 0
errors = 0

for s in stocks:
    industry = s.get('industry') or ''
    sector = s.get('sector', '')
    symbol = s.get('symbol', '')
    name = s.get('name', '')
    
    is_bank = 'Bank' in industry
    is_insurance = 'Insurance' in industry
    
    if not is_bank and not is_insurance:
        continue
    
    if is_bank:
        print(f'🏦 {name} ({symbol})...', end=' ', flush=True)
        metrics = fetch_bank_metrics(symbol)
        if 'error' not in metrics:
            bank_count += 1
            roa = metrics.get('ROA', '?')
            cti = metrics.get('costToIncome', '?')
            print(f'ROA={roa}% | C/I={cti}%')
        else:
            errors += 1
            print(f'❌ {metrics["error"]}')
    
    elif is_insurance:
        print(f'🛡️ {name} ({symbol})...', end=' ', flush=True)
        metrics = fetch_insurance_metrics(symbol)
        if 'error' not in metrics:
            insurance_count += 1
            lr = metrics.get('lossRatio', '?')
            cr = metrics.get('combinedRatio', '?')
            print(f'LR={lr}% | CR={cr}%')
        else:
            errors += 1
            print(f'❌ {metrics["error"]}')
    
    s['sectorFinancials'] = metrics
    time.sleep(0.5)  # Rate limit

if not DRY_RUN:
    with open('/srv/ideas/stocks-data.json', 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f'\n✅ تم الحفظ في stocks-data.json')
else:
    print(f'\n⚠️ DRY RUN — ما انحفظ شي')

print(f'\n📊 النتائج:')
print(f'  بنوك: {bank_count}')
print(f'  تأمين: {insurance_count}')
print(f'  أخطاء: {errors}')

PYTHON

echo "✅ اكتمل $(date '+%H:%M:%S')"
