from typing import List, Dict

import torch
from transformers import AutoTokenizer, AutoModel

from server.models.model_server import ModelServerEntry


class ChatGLMEntry(ModelServerEntry):
    def __init__(self, model_path) -> None:
        super().__init__()
        self.tokenizer = None
        self.model = None
        self.model_path = model_path

    def activate(self, device: str) -> None:
        model = AutoModel.from_pretrained(self.model_path, trust_remote_code=True, device=device).eval()
        tokenizer = AutoTokenizer.from_pretrained(self.model_path, trust_remote_code=True)
        self.model = model
        self.tokenizer = tokenizer
        print("model and tokenizer loaded")

    def deactivate(self) -> None:
        del self.model
        del self.tokenizer
        self.model = None
        self.tokenizer = None
        torch.cuda.empty_cache()
        print("model and tokenizer cleared")

    def inference(self, batch: List[List[Dict[str, str]]], temperature=0.7) -> List[str]:
        text = batch[0]
        expecting = "user"
        history = []
        for entry in text:
            role = entry["role"]
            if role != expecting:
                history[-1] += entry["content"]
            else:
                history.append(entry["content"])
                expecting = "user" if expecting == "assistant" else "user"
        history_paired = [(history[i], history[i + 1]) for i in range(0, len(history) - 1, 2)]
        response, history = self.model.chat(self.tokenizer,
                                            history[-1],
                                            history=history_paired,
                                            temperature=temperature)
        return [response]
