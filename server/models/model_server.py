import threading
import time
from typing import List, Dict, Any

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


class ModelServerEntry:
    def __init__(self) -> None:
        pass

    def activate(self, device: str) -> None:
        raise NotImplementedError

    def deactivate(self) -> None:
        raise NotImplementedError

    def inference(self, batch: List[List[Dict[str, str]]], temperature: float) -> List[str]:
        pass


class ModelServer:
    def __init__(self, models: Dict[str, ModelServerEntry], available_devices: List[str]) -> None:
        self.active = False
        self.lock = threading.Lock()
        self.models = dict()
        self.devices = dict()
        for model in models:
            self.models[model] = {
                "entry": models[model],
                "device": None,
                "lock": threading.Lock(),
                "pending": [],  # list of (message, temperature, callback)
                "last_used": 0,  # time.time()
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
                    time.sleep(0.2)
                    with self.lock:
                        if not self.active:
                            break

                    with self.models[model]["lock"]:
                        if self.models[model]["device"] is None:
                            continue
                        if len(self.models[model]["pending"]) == 0:
                            # if time.time() - self.models[model]["last_used"] > 600:
                            #     # check last_used, if 10 minutes ago, deactivate
                            #     log({
                            #         "system": "deactivate because of timeout",
                            #         "model": model,
                            #         "device": self.models[model]["device"],
                            #     })
                            #     self.force_deactivate(model)
                            continue

                        # update last_used
                        self.models[model]["last_used"] = time.time()
                        batch_size = self.models[model]["batch_size"]
                        batch = []
                        if len(batch) < batch_size and len(self.models[model]["pending"]) > 0:
                            # in one batch, all messages should have the same temperature
                            messages, temperature, callback = self.models[model]["pending"][0]
                            batch.append((messages, temperature, callback))
                            self.models[model]["pending"].pop(0)
                        if len(batch) == 0:
                            continue
                        messages, temperature, callback = zip(*batch)
                        messages = list(messages)
                        temperature = temperature[0]
                        callback = list(callback)

                        def process_inference(msgs, temp, cbs):
                            try:
                                ret = self.models[model]["entry"].inference(msgs, temp)
                                for idx, cb in enumerate(cbs):
                                    cb(ret[idx])
                            except Exception:
                                import traceback
                                traceback.print_exc()
                                for cb in cbs:
                                    cb(None)

                        threading.Thread(target=process_inference, args=(messages, temperature, callback)).start()

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
