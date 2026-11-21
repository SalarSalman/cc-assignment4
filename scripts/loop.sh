#!/bin/bash
# usage: scripts/loop.sh <logfile>   (Ctrl+C to stop)
LOG=${1:-results/loop.log}
: > "$LOG"
while true; do
  CODE=$(curl -s -m 5 -o /tmp/loop.body -w "%{http_code}" --resolve emi.local:8082:127.0.0.1 \
    -X POST http://emi.local:8082/api/emi -H "Content-Type: application/json" \
    -d '{"principal":500000,"rate":12,"months":24}')
  POD=$(python3 -c "import json;print(json.load(open('/tmp/loop.body'))['servedBy'])" 2>/dev/null || echo "-")
  echo "$(date +%T) $CODE $POD" | tee -a "$LOG"
  sleep 0.3
done
