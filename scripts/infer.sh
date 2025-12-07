#!/bin/bash
set -e

CONFIG_FILE="configs\config_infer.yaml"

echo "======================================================"
echo "        INFER USING CONFIG: $CONFIG_FILE"
echo "======================================================"

echo "[INFO]:"
cat "$CONFIG_FILE"
echo "------------------------------------------------------"

$PYTHON_BIN inference.py --config "$CONFIG_FILE"

echo "======================================================"
echo "                 TRAINING DONE!"
echo "======================================================"
