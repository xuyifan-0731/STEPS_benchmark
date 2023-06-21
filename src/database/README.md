# DB Bench

## Quick Start
1. put data into `data/` folder.
2. Implement class `Agent` in `Agent.py`.
3. Run `Judge.py`.
4. Input agent name after seeing `>>>`.

Example:
```python
# Agent.py

# ...

class GPTAgent(Agent):
    def __init__(self):
        self.history = []
    
    def message(self, msg):
        self.history.append({"role": "user", "content": msg})
    
    def act(self):
        # requests
        return json.loads(text)
```
```bash
echo "GPTAgent()" | python Judge.py
```
