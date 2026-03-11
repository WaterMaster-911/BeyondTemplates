#!/usr/bin/env bash
source /opt/conda/bin/activate base

git clone -b v0.4.6.post4 https://github.com/sgl-project/sglang.git
cd sglang
pip install --upgrade pip
pip install -e "python[all]"
cd ..

python -m pip install -U sglang-router

set -euo pipefail

SGLANG_PORT=8080
MODEL_PATH="model-path"

BASE_URL="http://0.0.0.0:${SGLANG_PORT}/v1/"

mkdir -p logs pids

TIME_TAG=$(date +"%Y%m%d_%H%M%S")
SGLANG_LOG="${SGLANG_PORT}_${TIME_TAG}"

python -m sglang.launch_server \
  --model-path "${MODEL_PATH}" \
  --port "${SGLANG_PORT}" \
  --tp 1 \
  > "logs/server_${SGLANG_LOG}.log" 2>&1 &

echo $! > "pids/sglang_${SGLANG_LOG}.pid"
echo "Booting sglang... pid $(cat pids/sglang_${SGLANG_LOG}.pid)"

for _ in $(seq 1 180); do
  if curl -s -m 2 "${BASE_URL}" >/dev/null 2>&1; then
    echo "sglang ready at ${BASE_URL}"
    exit 0
  fi
  sleep 2
done

echo "ERROR: sglang not ready; see logs/server_${SGLANG_LOG}.log"
exit 1
