# Model Server

This is a lite weight server for local models.

## Quick Start

### Environment

This project is tested on Python 3.11.

```bash
conda install pytorch torchvision torchaudio pytorch-cuda=11.8 -c pytorch -c nvidia
pip install -r requirements.txt
```

### Start server

```bash
PYTHONPATH="/path/to/STEPS_benchmark/" python -m model_api
```

Default batch size is 8, you can modify `BATCH_SIZE` in `model_server.py` or change config(see below) to change this value.

### Command line arguments

All of these are optional.

`--model` select a model to activate when starting.
`--device` devices to deploy the model you just selected.
`--port` select a port to start server, default 9999.

Example:
```
PYTHONPATH="~/STEPS_benchmark/" python -m model_api --model chatglm2-6b --device cuda:0 cuda:1 cuda:2 cuda:3 --port 9998
```

### APIs

| API                         | data                                                                                                                           | usage                                                              |
|-----------------------------|--------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------|
| /api/v1/model_name/call     | `{"messages": [{"role": "user", "content": "hello"}, {"role": "agent", "content": "hi"}, ...], "temperature" (Optional): 0.7}` | call model inference method                                        |
| /api/v1/model_name/add      | `{"device" (Optional): "cuda:0"} `                                                                                             | add a model entity                                                 |
| /api/v1/model_name/remove   | `{}`                                                                                                                           | remove a model entity                                              |
| /api/v1/                    | `{}`                                                                                                                           | status of all models                                               |
| /api/v1/model_name/activate | `{}`                                                                                                                           | add if none is activated, do nothing if at least one entity exists |

`status: 0` ALWAYS means success or normal.

## Add Custom model

1. Implement ALL api of `ModelServerEntry` in `models/Entry.py`, and import it in `models/__init__.py`
2. Add model in `config.json`.

```json
{
  "internal_model_name": {
    "name": "ImplementedModelEntryName",
    "batch_size": 4, // Optional, default 8 (BATCH_SIZE)
    "params":
    // a list or a dict of parameters for model entry, this directly goes to your entry's parameter
  }
}
```

3. Run `model_api.py` with `--model internal_model_name --device cuda:0 cuda:1 ... --port 9999`

Using arguments is equivalent to calling `/api/v1/internal_model_name/add`.