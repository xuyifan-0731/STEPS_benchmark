<h1> How to run STEPS-Lite </h1>

# Set up the environment

> If you want to setup the lite environment, simply run `bash setup-lite.sh`. Otherwise, you can follow the instructions below to setup the environment step by step.

## STEP-I to STEP-III

There is no need to set up the environment for STEP-I to STEP-III. You can skip this section.

## STEP-IV: Resourcefulness

### Tool Calling (API-Bench)

```bash
pip install tree_sitter
```

### Tool Execution

TODO: yuhao

### Code

TODO: xx

## STEP-V: Decisiveness

### Operating System Interaction

TODO: yuhao

### Database Interaction

TODO: hanchen

### Agent Game

TODO: hanyu

# Download the data

# Run the evaluation script

```bash
python evaluate.py \
    --task configs/tasks/lite.yaml \
    --agent configs/agents/do_nothing.yaml
```
