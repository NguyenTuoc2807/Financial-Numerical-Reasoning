#!/bin/bash
set -e

CONFIG_FILE="configs\config_grpo.yaml"

echo "======================================================"
echo "        TRAINING GRPO USING CONFIG: $CONFIG_FILE"
echo "======================================================"

echo "[INFO]:"
cat "$CONFIG_FILE"
echo "------------------------------------------------------"

$PYTHON_BIN train_grpo.py --config "$CONFIG_FILE"

echo "======================================================"
echo "                 TRAINING DONE!"
echo "======================================================"
