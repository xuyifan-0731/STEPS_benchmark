# Create Your Agent

Two ways to do this.

## Method I: Implement directly by client

Step 1. Create a file named `your_own_agent.py` in the `src/agents` folder. Write the following code in the file:

```python
from typing import List
from src.agent import Agent

class YourOwnAgent(Agent):
    """This agent is a test agent, which does nothing. (return empty string for each action)"""

    def __init__(self, **kwargs) -> None:
        # load your model here
        super().__init__(**kwargs)

    def inference(self, history: List[dict]) -> str:
        """Inference with the given history. History is composed of a list of dict, each dict:
        {
            "role": str, # the role of the message, "user" or "agent" only
            "content": str, # the text of the message
        }
        """

        # Finally return a string as the output
        return "AAAAA"
```


Step 2. Add an import statement in `src/agents/__init__.py`:

```python
from .your_own_agent import YourOwnAgent
```

Step 3. Add your agent to the config file `configs/agents/your_own_agent.yaml`:

```yaml
module: "src.agents.YourOwnAgent" # The module path to your agent class
parameters:
    name: "Do-Nothing-Agent"
    key1: value1 # The parameters fed into the constructor of your agent class
    key2: value2 # The parameters fed into the constructor of your agent class
```

## Method II: Implement agent server

See [Model Server Implementation](./server/README.md) for more detailed instruction.

## Method III: fastchat model server

Please refer to：
https://github.com/xuyifan-0731/fastchat_server
to build fastchat server for local model, such as chatglm2-6b.
After building, you can refer to configs/agents/  for agent.yaml.
