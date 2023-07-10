import multiprocessing as mp
import time
import traceback
from typing import List, Dict, Any

from .models import *


class ModelServerError(ValueError):
    pass


def process(queue, entry_class: type(ModelServerEntry), params, device, expected_q_length: mp.Value, signal: mp.Event):
    if type(params) is list:
        model = entry_class(*params)
    else:
        model = entry_class(**params)
    model.activate(device)
    while True:
        batch = queue.get()
        if queue.qsize() < expected_q_length.value:  # this number can be further optimized
            signal.set()
        data, temperature, conns = list(zip(*batch))
        print("batch size", len(data))
        try:
            result = model.inference(data, temperature[0])
        except Exception:
            traceback.print_exc()
            result = [None]
        for conn, r in zip(conns, result):
            conn.send(r)


def make_batch(queue_in: mp.Queue, queue_out: mp.Queue, batch_size: int, signal: mp.Event):
    while True:
        signal.wait()  # avoid running too quickly and making too much small batches; instead, wait for models
        signal.clear()
        tmp = [queue_in.get()]  # block until not empty
        while not queue_in.empty():
            tmp.append(queue_in.get_nowait())
        tmp.sort(key=lambda x: x[1])  # sort by temperature
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
        self.batching_signal = mp.Event()
        self.batching_signal.set()
        self.entity_num = mp.Value("i", 0)
        self.batcher = mp.Process(target=make_batch, args=(self.queue, self.batched_queue, 8, self.batching_signal))
        self.batcher.start()

    def add(self, device: str):
        p = mp.Process(target=process, args=(self.batched_queue, self.entry_class, self.params, device,
                                             self.entity_num, self.batching_signal))
        p.start()
        with self.lock:
            self.entities[device] = p
            self.entity_num.value = len(self.entities)

    def remove(self, device: str = None):
        p = self.entities[device]
        p.terminate()
        with self.lock:
            del self.entities[device]
            self.entity_num.value = len(self.entities)

    def enqueue(self, data: list[dict[str, str]], temperature: float, conn):
        if temperature is None:
            temperature = 0.7
        self.queue.put((data, temperature, conn))
        if self.batched_queue.qsize() < len(self.entities):
            self.batching_signal.set()
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

    def add(self, model_name: str, device: str = None) -> None:
        with self.lock:
            if model_name not in self.managers:
                if model_name not in self.models:
                    raise ModelServerError("Model not found")
                manager = ModelManager(eval(self.models[model_name]["name"]), self.models[model_name]["params"])
                self.managers[model_name] = manager
            else:
                manager = self.managers[model_name]
        if not device:
            device = self.find_device(model_name)
        else:
            with self.lock:
                self.devices[device] = model_name
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
