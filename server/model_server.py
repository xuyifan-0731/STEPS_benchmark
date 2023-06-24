import threading
import time
from typing import List, Dict, Any

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


class ModelServer:
    def __init__(self, models: Dict[str, ModelServerEntry], available_devices: List[str]) -> None:
        self.active = False
        self.lock = threading.Lock()
        self.models = dict()
        self.devices = dict()
        self.thread = None
        for model in models:
            self.models[model] = {
                "entry": models[model],
                "device": None,
                "lock": threading.Lock(),
                "pending": [],  # list of (message, temperature, callback)
                "last_used": .0,  # time.time()
                "batch_size": 6,  # number of messages in one batch
            }
        for device in available_devices:
            self.devices[device] = {
                "model": None,
            }

    def activate(self, model_name: str) -> str:
        if model_name not in self.models:
            raise ModelServerError("Model %s not found" % model_name)

        with self.models[model_name]["lock"]:
            # check if already activated
            device = self.models[model_name]["device"]
            if device:
                return device

            # update last_used
            self.models[model_name]["last_used"] = time.time()

            # find a device
            for device in self.devices:
                if self.devices[device]["model"] is None:
                    self.devices[device]["model"] = model_name
                    self.models[model_name]["device"] = device
                    self.models[model_name]["entry"].activate(device)
                    return device

            raise ModelServerError("No available device")

    def deactivate(self, model_name: str) -> None:
        if model_name not in self.models:
            raise ModelServerError("Model %s not found" % model_name)

        with self.models[model_name]["lock"]:
            device = self.models[model_name]["device"]
            if device is None:
                raise ModelServerError("Model %s is not activated" % model_name)
            self.models[model_name]["entry"].deactivate()
            self.models[model_name]["device"] = None
            self.devices[device]["model"] = None
            self.models[model_name]["pending"] = []
            return

    def status(self) -> Dict[str, Any]:
        models = dict()  # { active: bool, keys: int, your_status: bool }
        for model in self.models:
            models[model] = {
                "active": self.models[model]["device"] is not None,
            }
        available_device_count = len([device for device in self.devices if self.devices[device]["model"] is None])
        return {
            "models": models,
            "available_device_count": available_device_count,
        }

    def register(self, model, messages, temperature, callback):
        with self.models[model]["lock"]:
            if self.models[model]["device"] is None:
                raise ModelServerError("Model %s is not activated" % model)
            self.models[model]["pending"].append((messages, temperature, callback))

    def start(self):
        with self.lock:
            if self.active:
                raise ModelServerError("Server is already running.")
            self.active = True

        def work():
            print("Model server started.")

            def start_model_entry(model):
                while True:
                    with self.lock:
                        if not self.active:
                            break

                    with self.models[model]["lock"]:
                        if self.models[model]["device"] is None:
                            continue
                        if len(self.models[model]["pending"]) == 0:
                            time.sleep(0.1)
                            continue

                        # update last_used
                        self.models[model]["last_used"] = time.time()
                        batch_size = self.models[model]["batch_size"]
                        for message, temperature, callback in self.models[model]["pending"]:
                            try:
                                ret = self.models[model]["entry"].inference(message, temperature)
                                callback(ret[0])
                            except Exception:
                                import traceback
                                traceback.print_exc()
                                callback(None)

            model_threads = dict()

            for model in self.models:
                model_threads[model] = threading.Thread(target=start_model_entry, args=(model,))
                model_threads[model].start()

            for model in model_threads:
                model_threads[model].join()

        self.thread = threading.Thread(target=work)
        self.thread.start()

    def stop(self):
        with self.lock:
            if not self.active:
                raise RuntimeError("Server is not running.")
            self.active = False

        self.thread.join()

    def __del__(self):
        with self.lock:
            if self.active:
                self.stop()
        for model in self.models:
            with self.models[model]["lock"]:
                if self.models[model]["device"] is None:
                    continue
                self.models[model]["entry"].deactivate()


if __name__ == '__main__':
    model_server = ModelServer({"test": None}, ["cpu"])
    # server_thread = threading.Thread(target=model_server.start)
    # server_thread.start()
    model_server.start()
    time.sleep(2)
    print(model_server.status("test"))
    model_server.stop()
