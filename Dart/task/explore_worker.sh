#!/usr/bin/env bash
set -euo pipefail

# ===== Fixed paths =====
TASKS="queue_explore/tasks.pending.jsonl"
LOCK="queue_explore/tasks.lock"
CLAIMED_DIR="claimed_explore"
RESULTS="results_explore/stream.jsonl"
mkdir -p "$CLAIMED_DIR"

# ===== Claim and loop control =====
BATCH=${BATCH:-64}       # Number of lines to claim per batch
SLEEP_SEC=${SLEEP_SEC:-5}  # Sleep seconds when no tasks
IDLE_MAX=${IDLE_MAX:-0}    # Max consecutive idle loops; 0=never exit

# ===== Inference parameters (align with start_server.sh) =====
BASE_URL="http://0.0.0.0:8080/v1/"
MODEL_NAME="Llama-3.2-3B-Instruct"
PIPELINE="judging/dart_pipeline.py"
BATCH_SIZE=64
REPEAT=16
MAX_WORKERS=64
MAX_TOKENS=$((4 * 1024))
TEMPERATURE=0.1

# On interrupt, only clean up temp output, do not delete claim (leave for recycle script)
out=""
trap '[[ -n "${out:-}" && -f "$out" ]] && rm -f "$out" || true' INT TERM

idle=0
while :; do
  # 1) Atomically claim a batch -> temp file
  tmp="batch_$$.jsonl"
  (
    flock -x 200
    [[ -f "$TASKS" ]] || { : > "$tmp"; exit 0; }
    head -n "${BATCH}" "$TASKS" > "$tmp" || true
    sed -i "1,${BATCH}d" "$TASKS" || true
  ) 200>"$LOCK"

  # 2) No tasks -> sleep/maybe exit
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

  # 3) Generate claim (holds this batch; exists=not ACKed)
  runid="claim_$(date +%s)_$$"
  claim="${CLAIMED_DIR}/${runid}.jsonl"
  mv "$tmp" "$claim"
  echo "Claimed $(wc -l < "$claim") lines -> $claim"

  # 4) Batch inference
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
    --prompt_mode explore \
    --temperature "$TEMPERATURE" || rc=$?

  # 5) On success, write results and ACK; on failure, keep claim for recycle
  if [[ $rc -eq 0 && -s "$out" ]]; then
    cat "$out" >> "$RESULTS"
    rm -f "$out" "$claim"   # ACK
    out=""
    echo "Done & ACK: $runid"
  else
    echo "WARN: pipeline failed or empty output; keep claim for requeue: $claim (rc=$rc)"
    [[ -f "$out" ]] && rm -f "$out" || true
    out=""
    # Do not break loop, continue to claim next batch
  fi
done
