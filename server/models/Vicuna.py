import gc
from typing import Iterable, List, Dict

import torch
from transformers import LogitsProcessorList, TemperatureLogitsWarper, AutoTokenizer, AutoModelForCausalLM

from .Entry import ModelServerEntry


def is_partial_stop(output, stop_str):
    """Check whether the output contains a partial stop str."""
    for i in range(0, min(len(output), len(stop_str))):
        if stop_str.startswith(output[-i:]):
            return True
    return False


def prepare_logits_processor(
        temperature: float
) -> LogitsProcessorList:
    processor_list = LogitsProcessorList()
    # TemperatureLogitsWarper doesn't accept 0.0, 1.0 makes it a no-op so we skip two cases.
    if temperature >= 1e-5 and temperature != 1.0:
        processor_list.append(TemperatureLogitsWarper(temperature))
    return processor_list


def generate_stream(
        model, tokenizer, params, device, context_len=2048, stream_interval=2
):
    prompt = params["prompt"]
    len_prompt = len(prompt)
    temperature = float(params.get("temperature", 1.0))

    max_new_tokens = int(params.get("max_new_tokens", 256))
    stop_str = params.get("stop", None)
    echo = bool(params.get("echo", True))
    stop_token_ids = params.get("stop_token_ids", None) or []
    stop_token_ids.append(tokenizer.eos_token_id)

    logits_processor = prepare_logits_processor(
        temperature
    )

    input_ids = tokenizer(prompt).input_ids
    output_ids = list(input_ids)

    if model.config.is_encoder_decoder:
        max_src_len = context_len
    else:
        max_src_len = context_len - max_new_tokens - 8

    input_ids = input_ids[-max_src_len:]
    input_echo_len = len(input_ids)

    if model.config.is_encoder_decoder:
        encoder_output = model.encoder(
            input_ids=torch.as_tensor([input_ids], device=device)
        )[0]
        start_ids = torch.as_tensor(
            [[model.generation_config.decoder_start_token_id]],
            dtype=torch.int64,
            device=device,
        )

    past_key_values = out = None
    for i in range(max_new_tokens):
        if i == 0:
            if model.config.is_encoder_decoder:
                out = model.decoder(
                    input_ids=start_ids,
                    encoder_hidden_states=encoder_output,
                    use_cache=True,
                )
                logits = model.lm_head(out[0])
            else:
                out = model(torch.as_tensor([input_ids], device=device), use_cache=True)
                logits = out.logits
            past_key_values = out.past_key_values
        else:
            if model.config.is_encoder_decoder:
                out = model.decoder(
                    input_ids=torch.as_tensor([[token]], device=device),
                    encoder_hidden_states=encoder_output,
                    use_cache=True,
                    past_key_values=past_key_values,
                )

                logits = model.lm_head(out[0])
            else:
                out = model(
                    input_ids=torch.as_tensor([[token]], device=device),
                    use_cache=True,
                    past_key_values=past_key_values,
                )
                logits = out.logits
            past_key_values = out.past_key_values

        if logits_processor:
            tmp_output_ids = None
            last_token_logits = logits_processor(tmp_output_ids, logits[:, -1, :])[0]
        else:
            last_token_logits = logits[0, -1, :]

        if device == "mps":
            # Switch to CPU by avoiding some bugs in mps backend.
            last_token_logits = last_token_logits.float().to("cpu")

        if temperature < 1e-5:  # greedy
            token = int(torch.argmax(last_token_logits))
        else:
            probs = torch.softmax(last_token_logits, dim=-1)
            token = int(torch.multinomial(probs, num_samples=1))

        output_ids.append(token)

        if token in stop_token_ids:
            stopped = True
        else:
            stopped = False

        if i % stream_interval == 0 or i == max_new_tokens - 1 or stopped:
            if echo:
                tmp_output_ids = output_ids
                rfind_start = len_prompt
            else:
                tmp_output_ids = output_ids[input_echo_len:]
                rfind_start = 0

            output = tokenizer.decode(
                tmp_output_ids,
                skip_special_tokens=True,
                spaces_between_special_tokens=False,
            )

            partially_stopped = False
            if stop_str:
                if isinstance(stop_str, str):
                    pos = output.rfind(stop_str, rfind_start)
                    if pos != -1:
                        output = output[:pos]
                        stopped = True
                    else:
                        partially_stopped = is_partial_stop(output, stop_str)
                elif isinstance(stop_str, Iterable):
                    for each_stop in stop_str:
                        pos = output.rfind(each_stop, rfind_start)
                        if pos != -1:
                            output = output[:pos]
                            stopped = True
                            break
                        else:
                            partially_stopped = is_partial_stop(output, each_stop)
                            if partially_stopped:
                                break
                else:
                    raise ValueError("Invalid stop field type.")

            # prevent yielding partial stop sequence
            if not partially_stopped:
                yield {
                    "text": output,
                    "usage": {
                        "prompt_tokens": input_echo_len,
                        "completion_tokens": i,
                        "total_tokens": input_echo_len + i,
                    },
                    "finish_reason": None,
                }

        if stopped:
            break

    # finish stream event, which contains finish reason
    if i == max_new_tokens - 1:
        finish_reason = "length"
    elif stopped:
        finish_reason = "stop"
    else:
        finish_reason = None

    yield {
        "text": output,
        "usage": {
            "prompt_tokens": input_echo_len,
            "completion_tokens": i,
            "total_tokens": input_echo_len + i,
        },
        "finish_reason": finish_reason,
    }

    # clean
    del past_key_values, out


class VicunaEntry(ModelServerEntry):
    def __init__(self, model_path: str):
        super().__init__()
        self.model = None
        self.tokenizer = None
        self.model_path = model_path

    def inference(self, batch: List[List[Dict[str, str]]], temperature: float = 0.7) -> List[str]:
        ret = []
        for h in batch:
            gen_params = {
                "model": self.model_path,
                "prompt": self.get_prompt([h]),
                "temperature": temperature,
                "stop": None,
                "stop_token_ids": None,
                "echo": False,
            }
            output_stream = generate_stream(self.model, self.tokenizer, gen_params, self.model.device)
            output_text = ""
            for outputs in output_stream:
                output_text = outputs["text"]
            ret.append(output_text)
        return ret

    def get_prompt(self, batch: List[List[Dict[str, str]]]) -> str:
        seps = [" ", "</s>"]
        system = "A chat between a curious user and an artificial intelligence assistant. " \
                 "The assistant gives helpful, detailed, and polite answers to the user's questions."
        ret = system + seps[0]
        history = batch[0]
        for i, entry in enumerate(history):
            role = entry["role"]
            message = entry["content"]
            role = role.upper()
            if message:
                ret += role + ": " + message + seps[i % 2]
            else:
                ret += role + ":"
        ret += "ASSISTANT:"
        return ret

    def activate(self, device: str) -> None:
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_path, use_fast=False, revision="main"
        )
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_path,
            low_cpu_mem_usage=True,
            torch_dtype=torch.float16,
        ).to(device).eval()

    def deactivate(self) -> None:
        del self.model
        del self.tokenizer
        self.model = None
        self.tokenizer = None
        gc.collect()
        torch.cuda.empty_cache()
        print("model and tokenizer cleared")


if __name__ == '__main__':
    entry = VicunaEntry("/workspace/xuyifan/checkpoints/vicuna/7B")
    entry.activate("cuda:1")
    print(entry.inference([[
        {"role": "user", "content": "Hello!"},
        {"role": "assistant", "content": "Hi."},
        {"role": "user", "content": "Introduce yourself"}
    ], [
        {"role": "user", "content": "how are you today"},
        {"role": "assistant", "content": "I'm fine thank you, and you?"},
        {"role": "user", "content": "I'm fine, too"}
    ]], 0.3))
