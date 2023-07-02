from typing import List, Dict


class ModelServerEntry:
    def __init__(self) -> None:
        pass

    def activate(self, device: str) -> None:
        raise NotImplementedError

    def deactivate(self) -> None:
        raise NotImplementedError

    def inference(self, batch: List[List[Dict[str, str]]], temperature: float) -> List[str]:
        pass
