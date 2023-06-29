from typing import List, Dict

import torch
from transformers import AutoTokenizer, AutoModel

from .Entry import ModelServerEntry


class ChatGLMEntry(ModelServerEntry):
    def __init__(self, model_path) -> None:
        super().__init__()
        self.tokenizer = None
        self.model = None
        self.model_path = model_path

    def activate(self, device: str) -> None:
        model = AutoModel.from_pretrained(self.model_path, trust_remote_code=True, device=device,
                                          torch_dtype=torch.bfloat16).eval()
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

    def build_inputs(self, batch: list[list[dict[str, str]]]):
        ret = []
        for text in batch:
            expecting = "user"
            history = []
            for entry in text:
                role = entry["role"]
                if role != expecting:
                    history[-1] += entry["content"]
                else:
                    history.append(entry["content"])
                    expecting = "user" if expecting == "assistant" else "assistant"
            history_paired = [(history[i], history[i + 1]) for i in range(0, len(history) - 1, 2)]

            prompt = ""
            for i, (old_query, response) in enumerate(history_paired):
                prompt += "[Round {}]\n\n问：{}\n\n答：{}\n\n".format(i + 1, old_query, response)
            if text[-1]["role"] == "user":
                prompt += "[Round {}]\n\n问：{}\n\n答：".format(len(history_paired) + 1, history[-1])
            else:
                prompt = prompt.strip()  # remove /n/n at the end
            ret.append(prompt)
        return self.tokenizer(ret, padding=True, return_tensors="pt").to(self.model.device)

    def inference(self, batch: List[List[Dict[str, str]]], temperature=0.7) -> List[str]:
        inputs = self.build_inputs(batch)
        input_length = len(inputs.input_ids[0])
        outputs = self.model.generate(
            input_ids=inputs.input_ids,
            attention_mask=inputs.get("attention_mask", None),
            max_length=2048, do_sample=temperature != 0, temperature=temperature if temperature else 0.7,
        )

        output_ids = [output[input_length:] for output in outputs]
        result = self.tokenizer.batch_decode(output_ids, skip_special_tokens=True)
        return result
