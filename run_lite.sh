if [ -e config.sh ]; then
    source config.sh
else
    echo "'config.sh' does not exist, please create and write some variables first."
    exit 1
fi

python evaluate.py \
    --task configs/tasks/lite.yaml \
    --agent configs/agents/local/turbo.yaml \
    --workers 50