#!/bin/bash
set -e

CONFIG_FILE="configs\config_sft.yaml"

echo "======================================================"
echo "        TRAINING SFT USING CONFIG: $CONFIG_FILE"
echo "======================================================"

echo "[INFO]:"
cat "$CONFIG_FILE"
echo "------------------------------------------------------"

$PYTHON_BIN train_sft.py --config "$CONFIG_FILE"

echo "======================================================"
echo "                 TRAINING DONE!"
echo "======================================================"
