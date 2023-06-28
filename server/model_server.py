import multiprocessing as mp
import time
import traceback
from typing import List, Dict, Any

import dill

from .models import *

"""

In this file, two classes are defined:

1. ModelServerEntry: the entry point of the model server, which controls the deployment of a model

- device: property, the device to run the model, None for not deployed
- activate(device: str): method, deploy the model on `device`
- deactivate(): method, deactivate the model
- inference(batch: list[dict[str, str]]): method, run inference on the model, return a list of str as the results

2. ModelServer: the model server, which controls the deployment of all models

- __init__(models: dict[str, ModelServerEntry], available_devices: list[str]): constructor, `models` is a dict of 
model entry name to ModelServerEntry, `available_devices` is a list of available devices 
- models: property, the list of entries 
- activate(model_name: str, key: str): method, deploy the model `model_name`, return the device name 
- deactivate(model_name: str, key: str): method, remove key from all keys. If not key is left, the model will be 
deactivated

"""


class ModelServerError(ValueError):
    pass


def process(queue, model):
    model = dill.loads(model)
    while True:
        batch = queue.get()
        data, temperature, conns = list(zip(*batch))
        print("batch size", len(data))
        try:
            result = model.inference(data, temperature[0])
        except Exception:
            traceback.print_exc()
            result = [None]
        for conn, r in zip(conns, result):
            conn.send(r)


def make_batch(queue_in: mp.Queue, queue_out: mp.Queue, batch_size: int):
    while True:
        tmp = [queue_in.get()]  # block until not empty
        while not queue_in.empty():
            tmp.append(queue_in.get_nowait())
        tmp.sort(key=lambda x: x[1])    # sorut by temperature
        t = tmp[0][1]
        batch = []
        for i in tmp:
            if i[1] == t and len(batch) < batch_size:
                batch.append(i)
            else:
                queue_out.put(batch)
                batch = [i]
                t = i[1]
        queue_out.put(batch)


class ModelManager:
    def __init__(self, entry_class: type[ModelServerEntry], params: [dict | list]) -> None:
        self.params = params
        self.entry_class = entry_class
        self.lock = mp.Lock()
        self.entities = {}
        self.queue = mp.Queue()
        self.batched_queue = mp.Queue()
        self.manager = mp.Manager()
        self.shared_dict = self.manager.dict()
        self.batcher = mp.Process(target=make_batch, args=(self.queue, self.batched_queue, 4))
        self.batcher.start()

    def add(self, device: str):
        if type(self.params) is list:
            model = self.entry_class(*self.params)
        else:
            model = self.entry_class(**self.params)
        model.activate(device)
        model = dill.dumps(model)
        p = mp.Process(target=process, args=(self.batched_queue, model))
        p.start()
        with self.lock:
            self.entities[device] = (model, p)

    def remove(self, device: str = None):
        model, p = self.entities[device]
        p.terminate()
        model.deactivate()
        with self.lock:
            del self.entities[device]

    def enqueue(self, data: list[dict[str, str]], temperature: float, conn):
        if temperature is None:
            temperature = 0.7
        self.queue.put((data, temperature, conn))
        print(self.queue.qsize())


class ModelServer:
    def __init__(self, models: Dict[str, Dict[str, str]], available_devices: List[str]) -> None:
        self.active = False
        self.lock = mp.Lock()
        self.models = models
        self.model_devices: dict[str, list] = {}
        self.devices: dict[str, [str]] = {device: None for device in available_devices}
        self.managers = {}

    def find_device(self, model_name: str) -> str:
        with self.lock:
            for device in self.devices:
                if not self.devices[device]:
                    self.devices[device] = model_name
                    return device
            raise ModelServerError("All devices occupied")

    def add(self, model_name: str) -> None:
        with self.lock:
            if model_name not in self.managers:
                if model_name not in self.models:
                    raise ModelServerError("Model not found")
                manager = ModelManager(eval(self.models[model_name]["name"]), self.models[model_name]["params"])
                self.managers[model_name] = manager
            else:
                manager = self.managers[model_name]
        device = self.find_device(model_name)
        manager.add(device)
        with self.lock:
            self.model_devices.setdefault(model_name, []).append(device)

    def remove(self, model_name: str) -> None:
        with self.lock:
            if model_name not in self.managers:
                raise ModelServerError("No model activated")
            manager = self.managers[model_name]
            device = self.model_devices[model_name].pop()
        manager.remove(device)
        with self.lock:
            self.devices[device] = None

    def status(self, model_name: str = None) -> Dict[str, Any]:
        if not model_name:
            return self.model_devices
        return {model_name: self.model_devices[model_name]}

    def register(self, model, messages, temperature, callback):
        self.managers[model].enqueue(messages, temperature, callback)

    def stop(self):
        with self.lock:
            if not self.active:
                raise RuntimeError("Server is not running.")
            self.active = False

        for manager in self.managers.values():
            manager.remove()

    def __del__(self):
        with self.lock:
            if self.active:
                self.stop()


if __name__ == '__main__':
    model_server = ModelServer({"test": None}, ["cpu"])
    # server_thread = threading.Thread(target=model_server.start)
    # server_thread.start()
    time.sleep(2)
    print(model_server.status("test"))
    model_server.stop()
