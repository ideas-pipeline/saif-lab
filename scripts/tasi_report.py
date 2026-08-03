#!/usr/bin/env python3
"""تقرير تاسي اليومي - يجلب البيانات من API الرسمي ويركب تقرير مفصل"""

import requests
import json
from datetime import datetime

API_URL = 'https://tadawulallshareindex.com/data/live-prices.json'

def fetch_data():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept': 'application/json',
    }
    resp = requests.get(API_URL, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.json()


def get_top_movers(stocks, key='volume', top_n=5, rising=True):
    """إرجاع الأسهم الأكثر ارتفاعاً أو انخفاضاً"""
    filtered = [s for s in stocks if s.get('change_percent', 0) > 0] if rising else [s for s in stocks if s.get('change_percent', 0) < 0]
    sorted_stocks = sorted(filtered, key=lambda x: x.get(key, 0), reverse=True)
    return sorted_stocks[:top_n]


def get_top_active(stocks, key='volume', top_n=5):
    """الأكثر نشاطاً حسب الحجم"""
    return sorted(stocks, key=lambda x: x.get(key, 0), reverse=True)[:top_n]


def format_number(n):
    """تنسيق الأرقام الكبيرة"""
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n/1_000:.0f}K"
    return str(n)


def build_report():
    data = fetch_data()
    today = datetime.now().strftime('%A %d %B %Y')
    market = data.get('market_status', 'unknown')
    is_closed = market == 'closed'

    # ── المؤشر العام ──
    tasi = data.get('tasi', {})
    index_val = tasi.get('value', '—')
    change_val = tasi.get('change', 0)
    change_pct = tasi.get('change_percent', 0)
    volume = tasi.get('volume', 0)
    advancers = tasi.get('advancers', 0)
    decliners = tasi.get('decliners', 0)
    unchanged = tasi.get('unchanged', 0)
    date_str = tasi.get('date', today)

    # ── الأسهم ──
    stocks = data.get('stocks', [])

    # ── القطاعات ──
    sectors = data.get('sectors', [])

    # ── أكثر ارتفاعاً ──
    top_risers = get_top_movers(stocks, key='change_percent', top_n=3, rising=True)

    # ── أكثر انخفاضاً ──
    top_fallers = get_top_movers(stocks, key='change_percent', top_n=3, rising=False)

    # ── الأكثر نشاطاً ──
    top_active = get_top_active(stocks, key='volume', top_n=3)

    # ── اتجاه المؤشر ──
    if change_pct > 0:
        direction_icon = '📈'
        direction_arrow = '▲'
    elif change_pct < 0:
        direction_icon = '📉'
        direction_arrow = '▼'
    else:
        direction_icon = '⚪'
        direction_arrow = '—'

    # ── القطاعات المرتبة ──
    green_sectors = []
    red_sectors = []
    for s in sectors:
        cp = s.get('change_percent', 0)
        if cp > 0:
            green_sectors.append((s.get('name', s.get('slug', '')), f"+{cp:.2f}"))
        elif cp < 0:
            red_sectors.append((s.get('name', s.get('slug', '')), f"{cp:.2f}"))

    green_sectors.sort(key=lambda x: float(x[1].replace('+', '')), reverse=True)
    red_sectors.sort(key=lambda x: float(x[1]))

    # ── بناء التقرير ──
    status_text = "سوق مغلق 🔒" if is_closed else "سوق مفتوح 🟢"
    if date_str:
        status_text += f" — بيانات {date_str}"

    report = f"""📊 **ملخص مؤشر تاسي اليومي**
📅 {today}

**المؤشر:** {index_val:,.2f} نقطة | {direction_icon} {direction_arrow} {change_pct:+.2f}% ({change_val:+.2f})

**حجم التداول:** {format_number(volume)} سهم
**قيمة التداول:** {format_number(tasi.get('value_traded', 0))} ريال

**{status_text}**

**📈 أبرز الأسهم:**
🟢 ارتفعت: {advancers} سهم
🔴 انخفضت: {decliners} سهم
⚪️ استقرت: {unchanged} سهم

**🏆 الأكثر ارتفاعاً:**
"""

    for s in top_risers:
        sym = s.get('slug', s.get('symbol', '')).upper()
        cp = s.get('change_percent', 0)
        report += f"• {sym} +{cp:.2f}%\n"

    report += "\n**📉 الأكثر انخفاضاً:**\n"
    for s in top_fallers:
        sym = s.get('slug', s.get('symbol', '')).upper()
        cp = s.get('change_percent', 0)
        report += f"• {sym} {cp:.2f}%\n"

    report += "\n**🔵 الأكثر نشاطاً:**\n"
    for s in top_active:
        sym = s.get('slug', s.get('symbol', '')).upper()
        vol = format_number(s.get('volume', 0))
        report += f"• {sym} — {vol} سهم\n"

    if green_sectors or red_sectors:
        report += "\n**📊 القطاعات:**\n"
        if green_sectors:
            report += '\n'.join([f"🟢 {s} +{v}%" for s, v in green_sectors[:4]]) + '\n'
        if red_sectors:
            report += '\n'.join([f"🔴 {s} {v}%" for s, v in red_sectors[:4]])

    report += "\n\n🔗 المصدر: tadawulallshareindex.com"
    print(report)
    return report


if __name__ == '__main__':
    build_report()