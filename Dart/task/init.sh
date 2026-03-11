set -euo pipefail

mkdir -p queue claimed results logs pids

cp -f judging/data/limo_processed.jsonl queue/tasks.pending.jsonl

: > results/stream.jsonl
: > queue/tasks.lock

echo "Initialized queue/tasks.pending.jsonl"
wc -l queue/tasks.pending.jsonl
