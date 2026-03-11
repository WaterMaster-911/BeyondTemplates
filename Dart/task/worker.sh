#!/usr/bin/env bash
set -euo pipefail

TASKS="queue/tasks.pending.jsonl"
LOCK="queue/tasks.lock"
CLAIMED_DIR="claimed"
RESULTS="results/stream.jsonl"
mkdir -p "$CLAIMED_DIR"


BATCH=${BATCH:-64}       
SLEEP_SEC=${SLEEP_SEC:-5}  
IDLE_MAX=${IDLE_MAX:-0}    


BASE_URL="http://0.0.0.0:8080/v1/"
MODEL_NAME="Llama-3.2-3B-Instruct"
PIPELINE="judging/dart_pipeline.py"
BATCH_SIZE=64
REPEAT=4
MAX_WORKERS=64

MAX_TOKENS=$((4 * 1024))
TEMPERATURE=0.1

out=""
trap '[[ -n "${out:-}" && -f "$out" ]] && rm -f "$out" || true' INT TERM

idle=0
while :; do
  tmp="batch_$$.jsonl"
  (
    flock -x 200
    [[ -f "$TASKS" ]] || { : > "$tmp"; exit 0; }
    head -n "${BATCH}" "$TASKS" > "$tmp" || true
    sed -i "1,${BATCH}d" "$TASKS" || true
  ) 200>"$LOCK"


  if [[ ! -s "$tmp" ]]; then
    rm -f "$tmp"
    idle=$((idle+1))
    if (( IDLE_MAX>0 && idle>=IDLE_MAX )); then
      echo "No tasks left for $idle loops. Exit."
      break
    fi
    sleep "$SLEEP_SEC"
    continue
  fi
  idle=0


  runid="claim_$(date +%s)_$$"
  claim="${CLAIMED_DIR}/${runid}.jsonl"
  mv "$tmp" "$claim"
  echo "Claimed $(wc -l < "$claim") lines -> $claim"

  out="${claim}.out"
  rc=0
  python "$PIPELINE" \
    --input "$claim" \
    --output "$out" \
    --batch_size "$BATCH_SIZE" \
    --repeat "$REPEAT" \
    --max_workers "$MAX_WORKERS" \
    --base_url "$BASE_URL" \
    --model "$MODEL_NAME" \
    --max_tokens "$MAX_TOKENS" \
    --temperature "$TEMPERATURE" || rc=$?


  if [[ $rc -eq 0 && -s "$out" ]]; then
    cat "$out" >> "$RESULTS"
    rm -f "$out" "$claim"   # ACK
    out=""
    echo "Done & ACK: $runid"
  else
    echo "WARN: pipeline failed or empty output; keep claim for requeue: $claim (rc=$rc)"
    [[ -f "$out" ]] && rm -f "$out" || true
    out=""
  fi
done
