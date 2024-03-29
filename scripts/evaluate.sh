#!/bin/bash

script_path=$(realpath $0)
script_dir=$(dirname $script_path)
main_dir=$(dirname $script_dir)

ARGS="${main_dir}/evaluate.py \
       --agent $1 \
       --task $2"

TIMESTAMP=$(date +'%Y.%m.%d-%H:%M:%S')
EXP_NAME=${TIMESTAMP}

mkdir -p logs

run_cmd="python ${ARGS}"
echo $run_cmd
eval ${run_cmd} 2>&1 | tee logs/${EXP_NAME}.log
