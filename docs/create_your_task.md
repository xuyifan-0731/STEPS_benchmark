# Create your task

## Implement a task class

Create a folder `src/tasks/<your_task>`.

Create a file `src/tasks/<your_task>/task.py` to override the following methods: (You can refer to src.tasks.OSInteraction)

```python
from src.task import Task

class YourOwnTask(Task):
    def __init__(self, **config):
        # Pop the neccessary parameters from config
        super().__init__()

    @property
    def metrics(self): # Change the metrics if necessary
        return {"EM": lambda outputs, targets: len([1 for o, t in zip(outputs, targets) if o == t]) / min(len(outputs), len(targets))}

    def get_data(self): # return Dataset(Generic[T_INPUT, T_TARGET], List[DataPiece[T_INPUT, T_TARGET]]), T_INPUT and T_TARGET need to be json serializable
        raise NotImplementedError

    def predict_single(self, session, data_item): # return OUTPUT object, need to be json serializable
        raise NotImplementedError
```

Create a file `src/tasks/<your_task>/__init__.py` and write the following code:

```python
from .task import YourOwnTask
```

Import your task in `src/tasks/__init__.py`:

```python
from .<your_task> import YourOwnTask
```

## Put your data if necessary

Put your data in `data/<your_task>/*`.

## Create a task configuration file (YAML)

Create a file `configs/tasks/<your_task>.yaml` to specify your task's configuration:

```yaml
module: "src.tasks.YourOwnTask"
parameters:
    name: "your_task" # Necessary
    category: "your_category" # The sub-folder of output directory, i.e., your output and evaluation results will be saved at <output_root_dir>/<category>/*.json(l)
    key: value # the parameters in YourOwnTask's constructor
    key2: value2 # the parameters in YourOwnTask's constructor
```

## Execute Unit Test with DoNothingAgent

Run the following command to test your task:

```
python evaluate.py --task configs/tasks/<your_task>.yaml --agent configs/agents/do_nothing.yaml --workers 30
```

Check your output in `output/<timestamp>/<your_task>`.

## Write a guidance for your task

Write your guidance in `docs/guide_for_each_task.md`.
