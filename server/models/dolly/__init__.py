import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

from .instruct_pipeline import InstructionTextGenerationPipeline
from .. import ModelServerEntry


class DollyEntry(ModelServerEntry):
    def __init__(self, model_path) -> None:
        self.tokenizer = None
        self.model = None
        self.model_path = model_path

    def construct_prompt(self, batch: list[list[dict[str, str]]]) -> list[str]:
        prompts = []
        for item in batch:
            prompt = "\n\n".join(["%s: %s" % (utter["role"], utter["content"]) for utter in item])
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

    def inference(self, batch: list[list[dict[str, str]]], temperature=None) -> list[str]:
        torch.cuda.empty_cache()
        prompts = self.construct_prompt(batch)

        with torch.no_grad():
            try:
                return self.inference_dolly(prompts)
            except Exception:
                import traceback
                traceback.print_exc()
                return [""] * len(prompts)

    def inference_dolly(self, prompts):
        generate_text = InstructionTextGenerationPipeline(model=self.model, tokenizer=self.tokenizer)

        with torch.no_grad():
            try:
                outputs = generate_text(prompts)
            except Exception as e:
                print(f"exception inference {e}")
                return [""] * len(prompts)

        outputs = [output[0]["generated_text"].removeprefix("agent:").strip() for output in outputs]

        return outputs
