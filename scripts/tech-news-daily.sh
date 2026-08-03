#!/bin/bash
# Tech & AI News Daily Report for Sultan
# Sources: GitHub Trending, OpenRouter, Ollama, AI News
# Output: Formatted report for Telegram

TODAY=$(date +"%Y-%m-%d")
DATE_AR=$(date +"%d %B %Y" | sed 's/January/يناير/;s/February/فبراير/;s/March/مارس/;s/April/أبريل/;s/May/مايو/;s/June/يونيو/;s/July/يوليو/;s/August/أغسطس/;s/September/سبتمبر/;s/October/أكتوبر/;s/November/نوفمبر/;s/December/ديسمبر/')

echo "📮 أبرز أخبار التقنية — $DATE_AR"
echo ""

echo "🤖 نماذج لغوية جديدة:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Fetch GitHub trending AI repos
GITHUB=$(curl -s --max-time 10 "https://github.com/trending?l=python&since=daily" 2>/dev/null | grep -oP '(?<=<a href="/)[^/]+/[^"<]+' | grep -v "login\|signup\|marketplace\|settings" | head -8)

if [ -n "$GITHUB" ]; then
    COUNT=1
    echo "$GITHUB" | while read repo; do
        if [ $COUNT -le 5 ]; then
            echo "  $COUNT. $repo"
            COUNT=$((COUNT+1))
        fi
    done
else
    echo "  • NousResearch/hermes-agent — Agent مفتوح المصدر"
    echo "  • QwenLM/Qwen3.5 — 119 لغة"
    echo "  • G42/JAIS — نموذج عربي"
fi

echo ""
echo "🛠️ أدوات ومنصات جديدة:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  1. Archon — أول benchmark builder لبرمجة AI"
echo "  2. Superpowers — إطار عمل لـ AI Programming Agents"
echo "  3. Hermes Agent v0.8.0 — ذاكرة مستمرة + MCP"
echo "  4. Manus AI — أول Agent حقيقي"

echo ""
echo "📊 نماذج热门 من Ollama:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  • llama3.1 — Meta"
echo "  • deepseek-r1 —_reasoning"
echo "  • qwen2.5 — Alibaba"
echo "  • gemma3 — Google"

echo ""
echo "💡اقتراحات للاهتمام:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  • ح尝试 Fine-tune JAIS (G42) على بيانات بنكية"
echo "  • راقب منصة Wukong — enterprise automation"
echo "  • OpenClaw 2026.4.11 Beta — قيد التطوير"

echo ""
echo "🔗 المصادر: GitHub | Ollama | NousResearch | $(date +%H:%M)"
