#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 9 ]]; then
  echo "usage: $0 PYTHON CURAEVAL DATASET PROTOCOL STATE_BANK STATE_BANK_MANIFEST EVALUATOR SEED OUTPUT_DIR" >&2
  exit 2
fi

python_bin=$1
curaeval=$2
dataset=$3
protocol=$4
state_bank=$5
state_bank_manifest=$6
evaluator=$7
seed=$8
output_dir=$9
run_name="dp_square_probe_seed${seed}"

if [[ -e "$output_dir/TRAIN_COMPLETE" || -e "$output_dir/EVAL_COMPLETE" ]]; then
  echo "refusing to overwrite an existing probe task: $output_dir" >&2
  exit 1
fi
mkdir -p "$output_dir"

"$python_bin" "$curaeval/scripts/run_dp.py" \
  --dataset "$dataset" \
  --name "$run_name" \
  --output_dir "$output_dir/checkpoint" \
  --filter_key none \
  --epochs 100 \
  --steps_per_epoch 500 \
  --batch_size 256 \
  --rollout_n 0 \
  --horizon 500 \
  --seed "$seed" \
  --fast \
  >"$output_dir/train.log" 2>&1

mapfile -t checkpoints < <(find "$output_dir/checkpoint" -type f -name last.pth -print)
if [[ ${#checkpoints[@]} -ne 1 ]]; then
  echo "expected exactly one final checkpoint, found ${#checkpoints[@]}" >&2
  exit 1
fi
checkpoint=${checkpoints[0]}
sha256sum "$checkpoint" >"$output_dir/checkpoint.sha256"
touch "$output_dir/TRAIN_COMPLETE"

"$python_bin" "$evaluator" \
  --agent "$checkpoint" \
  --state-bank "$state_bank" \
  --state-bank-manifest "$state_bank_manifest" \
  --protocol "$protocol" \
  --policy-id all_data_probe \
  --training-seed "$seed" \
  --output "$output_dir/evaluation.json" \
  >"$output_dir/evaluate.log" 2>&1

sha256sum "$output_dir/evaluation.json" >"$output_dir/evaluation.sha256"
touch "$output_dir/EVAL_COMPLETE"
