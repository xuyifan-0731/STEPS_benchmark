from typing import List, Dict

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from server.models import ModelServerEntry


class OssatEntry(ModelServerEntry):
    def __init__(self, model_path) -> None:
        self.tokenizer = None
        self.model = None
        self.model_path = model_path

    def inference_moss(self, prompts):
        inputs = self.tokenizer(prompts, return_tensors="pt", padding=True, truncation=True)
        inputs = inputs.to(self.model.device)
        input_length = len(inputs.input_ids[0])  # length of padded sentences

        with torch.no_grad():
            try:
                output_ids = self.model.generate(
                    **inputs,
                    do_sample=True, max_new_tokens=256,
                )
            except Exception as e:
                print(f"exception inference {e}")
                return [""] * len(prompts)
        output_ids = [outputs[input_length:] for outputs in output_ids]
        outputs = self.tokenizer.batch_decode(output_ids, skip_special_tokens=True)
        return outputs

    def construct_prompt(self, batch: List[List[Dict[str, str]]]) -> List[str]:
        prompts = []
        for item in batch:
            prompt = ""
            for utter in item:
                if utter["role"] == "user":
                    prompt += "<|prompter|>{prompt}<|endoftext|>".format(prompt=utter["content"])
                elif utter["role"] == "assistant":
                    prompt += "<|assistant|>{prompt}<|endoftext|>".format(prompt=utter["content"])
            prompt += "<|assistant|>"
            prompts.append(prompt)
        return prompts

    def activate(self, device: str) -> None:
        model = AutoModelForCausalLM.from_pretrained(self.model_path, trust_remote_code=True).half().to(device)
        model = model.eval()
        tokenizer = AutoTokenizer.from_pretrained(self.model_path, trust_remote_code=True, padding_side="left")
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

    def inference(self, batch: List[List[Dict[str, str]]], temperature=None) -> List[str]:
        return self.inference_moss(self.construct_prompt(batch))
