#!/bin/bash
# Unlock protected files — requires password
CORRECT_HASH="d620182cd6dc78f87868c0f72111298abd3c53d80220475e02e0483c15289901"

read -s -p "🔑 Password: " pw
echo ""
INPUT_HASH=$(echo -n "$pw" | sha256sum | cut -d' ' -f1)

if [ "$INPUT_HASH" != "$CORRECT_HASH" ]; then
  echo "❌ Wrong password"
  exit 1
fi

WORKSPACE="/srv/ideas"
for f in \
  $WORKSPACE/scripts/*.sh \
  $WORKSPACE/scripts/*.py \
  $WORKSPACE/ideas-api/server.js \
  $WORKSPACE/ideas-api/logger.js \
  $WORKSPACE/ideas-site/mission-control.html \
  $WORKSPACE/ideas-site/index.html \
  $WORKSPACE/stocks-site/template.html \
  $WORKSPACE/AGENTS.md \
  $WORKSPACE/SOUL.md \
  $WORKSPACE/HEARTBEAT.md \
  $WORKSPACE/USER.md \
  $WORKSPACE/IDENTITY.md \
  $WORKSPACE/saif-invest/index.html \
  $WORKSPACE/saif-invest/app.js; do
  chmod 644 "$f" 2>/dev/null
done
echo "🔓 All files unlocked — run lock.sh when done"
