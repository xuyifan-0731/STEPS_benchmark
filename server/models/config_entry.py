from transformers import AutoTokenizer, AutoModelForCausalLM, AutoModel
from typing import List, Dict
import json
import torch

from .Entry import ModelServerEntry


def default_prompt(messages, args):
    init_prompt = args["init_prompt"]
    seperator = args["seperator"]
    user_name = args["user_name"]
    assistant_name = args["assistant_name"]
    prompt = init_prompt + seperator
    for utter in messages:
        role = user_name if utter["role"] == "user" else assistant_name
        prompt += role + ": " + utter["content"] + seperator
    prompt += assistant_name + ": "
    return prompt


def vicuna_prompt(messages, args):
    init_prompt = args["init_prompt"]
    seperator = args["seperator"]
    user_name = args["user_name"]
    assistant_name = args["assistant_name"]
    prompt = init_prompt + seperator
    for utter in messages:
        role = user_name if utter["role"] == "user" else assistant_name
        prompt += role + ": " + utter["content"] + seperator
    prompt += assistant_name + ":"
    return prompt


class ConfigEntry(ModelServerEntry):
    def __init__(self, config_path) -> None:
        with open(config_path, "r") as f:
            config = json.loads(f.read())
            f.close()
        self.tokenizer = None
        self.model = None
        self.config = config
        self.model_path = config.get("model_path")
        self.model_name = config.get("model_name")
        self.init_prompt = config.get("init_prompt")
        self.seperator = config.get("seperator")
        self.user_name = config.get("user_name")
        self.assistant_name = config.get("assistant_name")
        self.pad_token_id = config.get("pad_token_id", None)
        self.temperature = config.get("temperature")
        self.use_fast = config.get("use_fast", False)
        hf_model = config.get("hf_model", "AutoModelForCausalLM")
        if hf_model == "AutoModelForCausalLM":
            self.hf_model = AutoModelForCausalLM
        elif hf_model == "AutoModel":
            self.hf_model = AutoModel
        else:
            raise ValueError(f"hf_model {hf_model} not supported")

    def construct_prompt(self, batch: List[List[Dict[str, str]]]) -> List[str]:
        prompts = []
        for query in batch:
            if self.model_name.lower().find("vicuna") != -1:
                prompts.append(vicuna_prompt(query, self.config))
            else:
                prompts.append(default_prompt(query, self.config))
        # print("prompts: ", prompts)
        return prompts

    def activate(self, device: str) -> None:
        model = self.hf_model.from_pretrained(self.model_path, trust_remote_code=True).half().to(device)
        model = model.eval()
        self.model = model
        tokenizer = AutoTokenizer.from_pretrained(self.model_path, trust_remote_code=True, padding_side="left",
                                                  use_fast=self.use_fast)

        if self.pad_token_id is not None:
            tokenizer.pad_token_id = self.pad_token_id
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
        torch.cuda.empty_cache()
        prompts = self.construct_prompt(batch)
        inputs = self.tokenizer(prompts, return_tensors="pt", padding=True)
        inputs = inputs.to(self.model.device)
        input_length = len(inputs.input_ids[0])  # length of padded sentences

        with torch.no_grad():
            try:
                output_ids = self.model.generate(
                    input_ids=inputs.input_ids,
                    attention_mask=inputs.get("attention_mask", None),
                    max_length=2048, do_sample=True, temperature=temperature if temperature else self.temperature,
                )
            except Exception:
                import traceback
                traceback.print_exc()
                return [""] * len(prompts)
        output_ids = [outputs[input_length:] for outputs in output_ids]
        outputs = self.tokenizer.batch_decode(output_ids, skip_special_tokens=True)
        return outputs


if __name__ == "__main__":
    prompts = [[
        {
            "role": "user",
            "content": "I'm a bot."
        }
    ], [
        {
            "role": "user",
            "content": "I'm a bot."
        },
        {
            "role": "assistant",
            "content": "No, i'm a bot."
        },
        {
            "role": "user",
            "content": "How is the weather today?"
        }
    ]
    ]
    model = ConfigEntry("configs/vicuna-7B-new.json")
    model.activate("cuda:2")

    prompt = """A chat between a curious user and an artificial intelligence assistant. The assistant gives helpful, detailed, and polite answers to the user's questions. USER: Please choose a tool to solve the problem from the following list:

ModifyAlarm: This API modifies an alarm from the from_time to to_time.
GoogleFinance: This API arrange information of stock markets.
GoogleJobs: This API arrange information of certain jobs.
Time: This API returns current time in %Y-%m-%d %H:%M:%S format
GoogleImages: This API gives certain key of the given picture in google image.
QueryAlarm: This API finds all the alarm clocks that the user has set.
GoogleLocal: This API sets an alarm for the given time.
SendEmail: This tool sends an given email to given receivers
HomeDepot: This API allows you to scrape valuable product information in real time for your e-commerce automation without the deep knowledge of web scraping.
Ebay: This API allows you to scrape valuable product information of products in ebay.
Walmart: This API retrieves information about Walmart search results.
GoogleScolar: This API sets an alarm for the given time.
BookTrain: This API books a train ticket from the given from_city to the given to_city.
BookHotel: This API orders hotel rooms.
GoogleShopping: This API allows a user to scrape the results of a Google Shopping search.
AddAlarm: This API sets an alarm for the given time.
GoolePlay: This API allows you to get information of apps, games, movies or books from goole play store
SearchEmail: This API searches for emails matching given criteria.
BookFlight: This API books an air ticket from the given from_city to the given to_city.
Yelp: This API arrange merchant reviews.
Youtube: This API retrieves information about YouTube videos.
DeleteAlarm: This API removes an alarm for the given time.

You should strictly follow the format:

Choose Tool: [Name of the tool].

For example:

Choose Tool: BookTrain.

The problem is: Which companies do product manager positions in Beijing come from

 ASSISTANT:"""

    emb = model.tokenizer(prompt, return_tensors="pt").to("cuda:2")

    result = model.model.generate(**emb, max_new_tokens=1024)

    import IPython

    IPython.embed()
    # import time
    # time.sleep(10)
    # print(model.inference(prompts, temperature=0.7))
    # model.deactivate()
    # print("deactivited")
    # time.sleep(120)
