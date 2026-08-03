#!/bin/bash
# Lock all protected files (no password needed)
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
  chmod 444 "$f" 2>/dev/null
done
echo "🔒 All files locked"
