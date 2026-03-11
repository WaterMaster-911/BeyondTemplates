#!/usr/bin/env bash
set -euo pipefail

mkdir -p queue_explore claimed_explore results_explore logs pids

cp -f judging/data/limo_processed.jsonl queue/tasks.pending.jsonl

: > results_explore/stream.jsonl
: > queue_explore/tasks.lock

echo "Initialized queue_explore/tasks.pending.jsonl"
wc -l queue_explore/tasks.pending.jsonl
