AGENT_CONFIG=configs/agents/do_nothing.yaml # Change this into your agent config

python evaluate.py \
    --agent "$AGENT_CONFIG" \
    --task \
        configs/tasks/full/c-eval-val.yaml \
        configs/tasks/full/gsm8k_cn.yaml \
        configs/tasks/full/gsm8k_en.yaml \
        configs/tasks/full/bbh.yaml \
        configs/tasks/full/mmlu_zero_shot.yaml \
        configs/tasks/full/c-eval-test.yaml \
        configs/tasks/full/idiotqa.yaml \
        configs/tasks/full/math.yaml \
        configs/tasks/full/nqopen.yaml \
        configs/tasks/full/trivia_qa.yaml