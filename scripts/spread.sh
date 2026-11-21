#!/bin/bash
# usage: scripts/spread.sh <requests> <label>
N=${1:-30}; LABEL=${2:-run}
for i in $(seq 1 "$N"); do
  curl -s --resolve emi.local:8082:127.0.0.1 -X POST http://emi.local:8082/api/emi \
    -H "Content-Type: application/json" \
    -d '{"principal":500000,"rate":12,"months":24}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['servedBy'])"
done | tee results/spread-$LABEL.txt | sort | uniq -c
