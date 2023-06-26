import multiprocessing as mp
import time
from typing import List, Dict, Any, Callable

from server.models import ModelServerEntry

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


class ModelManager:
    def __init__(self, entry_class: type[ModelServerEntry]) -> None:
        self.entry_class = entry_class
        self.lock = mp.Lock()
        self.entities = {}
        self.queue = mp.Queue()

    def process(self, entry: ModelServerEntry):
        while True:
            data, temperature, callback = self.queue.get()
            result = entry.inference(data, temperature)
            callback(result)

    def add(self, device: str):
        model = self.entry_class()
        model.activate(device)
        p = mp.Process(target=self.process, args=(model,))
        p.start()
        with self.lock:
            self.entities[device] = (model, p)

    def remove(self, device: str = None):
        model, p = self.entities[device]
        p.terminate()
        model.deactivate()
        with self.lock:
            del self.entities[device]

    def enqueue(self, data: list[dict[str, str]], temperature: float, callback: Callable[[str], None]):
        self.queue.put((data, temperature, callback))


class ModelServer:
    def __init__(self, models: Dict[str, type[ModelServerEntry]], available_devices: List[str]) -> None:
        self.active = False
        self.lock = mp.Lock()
        self.models: dict[str, type[ModelServerEntry]] = models
        self.model_devices: dict[str, list] = {}
        self.devices: dict[str, [str]] = {device: None for device in available_devices}
        self.managers = {}

    def find_device(self) -> str:
        with self.lock:
            for device in self.devices:
                if not self.devices[device]:
                    return device
            raise ModelServerError("All devices occupied")

    def add(self, model_name: str) -> None:
        with self.lock:
            if model_name not in self.managers:
                if model_name not in self.models:
                    raise ModelServerError("Model not found")
                manager = ModelManager(self.models[model_name])
                self.managers[model_name] = manager
            else:
                manager = self.managers[model_name]
        device = self.find_device()
        manager.add(device)
        with self.lock:
            self.devices[device] = model_name
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
