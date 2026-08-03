#!/bin/bash
# تقرير تاسي اليومي - يُرسل عبر OpenClaw إلى Telegram
# يعمل كل يوم عمل الساعة 4:20 مساء (بعد إغلاق السوق)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPORT=$(python3 "$SCRIPT_DIR/tasi_report.py" 2>&1)

# إرسال التقرير عبر openclaw
openclaw message send \
  --channel telegram \
  --target 576845770 \
  --message "$REPORT"

echo "Done: $(date)"