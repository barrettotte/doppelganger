#!/bin/bash

# fine-tune model to clone specific character's voice

set -e

SECONDS=0

# configure CUDA devices (I want to ignore my smaller GPU)
export CUDA_VISIBLE_DEVICES=0

# fix cuda references
export LD_LIBRARY_PATH=$(uv run python -c "import nvidia.cudnn; import nvidia.cublas; print(list(nvidia.cudnn.__path__)[0] + '/lib:' + list(nvidia.cublas.__path__)[0] + '/lib')"):$LD_LIBRARY_PATH

# print divider for fine tuning steps.
# $1 - label
print_divider() {
    printf '%.s=' $(seq 1 80)
    printf "\n$1\n"
    printf '%.s=' $(seq 1 80)
    echo    
}

# print elapsed time in minutes/seconds
# $1 - label
# $2 - elapsed seconds
print_time() {
    echo "$1: $(($2 / 60))m $(($2 % 60))s"
}

uv sync
source .venv/bin/activate

# split and transcribe training/CHARACTER/train.wav into training/CHARACTER/train
print_divider "Splitting and transcribing audio"
python split_audio.py
split_duration=$SECONDS

# tokenize audio clips in training/CHARACTER/train to training/CHARACTER/dataset.jsonl
print_divider "Tokenizing audio"
python tokenize_audio.py
tokenize_duration=$SECONDS

# fine tune and save LoRA adapter to lora_adapters/CHARACTER
print_divider "Training"
python train_lora.py
train_duration=$SECONDS

# display durations
print_divider "Elapsed time"
print_time "Split/Transcribe" $split_duration
print_time "Tokenize" $tokenize_duration
print_time "Training" $train_duration

echo "-----------------"
total_duration=$((split_duration + tokenize_duration + train_duration))
print_time "Total" $total_duration

deactivate
