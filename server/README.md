# Model Server

This is a lite weight server for local models.

## Quick Start

### Start server

```bash
PYTHONPATH="/path/to/project/" python -m model_api.py
```

### Call

| API                       | data                                                                                                              | usage                       |
|---------------------------|-------------------------------------------------------------------------------------------------------------------|-----------------------------|
| /api/v1/model_name/call   | {"messages": [{"role": "user", "content": "hello"}, {"role": "agent", "content": "hi"}, ...], "temperature": 0.7} | call model inference method |
| /api/v1/model_name/add    | {}                                                                                                                | add a model entity          |
| /api/v1/model_name/remove | {}                                                                                                                | remove a model entity       |
| /api/v1/                  | {}                                                                                                                | status of all models        |

### Add Custom model

1. Implement `ModelServerEntry` in `models/Entry.py`, and import it in `models/__init__.py`
2. Add model in `config.json`.

```json
{
  "internal_model_name": {
    "name": "ImplementedModelEntryName",
    "params":
    // a list or a dict of parameters for model entry
  }
}
```
3. Run `model_api.py` with `--model internal_model_name --device cuda:0 cuda:1 ...`--port 9999