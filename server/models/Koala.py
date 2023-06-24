import tempfile
from typing import List, Dict, Optional, Any

import sentencepiece as spm
import torch
from transformers import AutoModelForCausalLM, PreTrainedTokenizer

from .Entry import ModelServerEntry


class LLaMATokenizer(PreTrainedTokenizer):
    """
    Construct a LLaMA tokenizer. Based on byte-level Byte-Pair-Encoding.
    Args:
        vocab_file (`str`):
            Path to the vocabulary file.
    """

    vocab_files_names = {"vocab_file": "tokenizer.model"}
    pretrained_vocab_files_map = {}
    model_input_names = ["input_ids", "attention_mask"]

    def __init__(
            self,
            vocab_file,
            unk_token="<unk>",
            bos_token="<s>",
            eos_token="</s>",
            sp_model_kwargs: Optional[Dict[str, Any]] = None,
            add_bos_token=False,
            add_eos_token=False,
            **kwargs,
    ):
        self.sp_model_kwargs = {} if sp_model_kwargs is None else sp_model_kwargs
        super().__init__(bos_token=bos_token, eos_token=eos_token, unk_token=unk_token, **kwargs)
        self.vocab_file = vocab_file
        self.add_bos_token = add_bos_token
        self.add_eos_token = add_eos_token
        self.sp_model = spm.SentencePieceProcessor(**self.sp_model_kwargs)

        with tempfile.NamedTemporaryFile() as tfile:
            with open(self.vocab_file, 'rb') as fin:
                tfile.write(fin.read())
                tfile.flush()
                tfile.seek(0)
            self.sp_model.Load(tfile.name)
        """ Initialisation"""
        self.add_special_tokens(dict(
            unk_token=unk_token,
            bos_token=bos_token,
            eos_token=eos_token,
        ))
        self.pad_token_id = self.unk_token_id

    @property
    def vocab_size(self):
        """Returns vocab size"""
        return self.sp_model.get_piece_size()

    @property
    def bos_token_id(self) -> Optional[int]:
        return self.sp_model.bos_id()

    @property
    def eos_token_id(self) -> Optional[int]:
        return self.sp_model.eos_id()

    def get_vocab(self):
        """Returns vocab as a dict"""
        vocab = {self.convert_ids_to_tokens(i): i for i in range(self.vocab_size)}
        vocab.update(self.added_tokens_encoder)
        return vocab

    def _tokenize(self, text):
        """Returns a tokenized string."""
        return self.sp_model.encode(text, out_type=str)

    def _convert_token_to_id(self, token):
        """Converts a token (str) in an id using the vocab."""
        return self.sp_model.piece_to_id(token)

    def _convert_id_to_token(self, index):
        """Converts an index (integer) in a token (str) using the vocab."""
        token = self.sp_model.IdToPiece(index)
        return token

    def convert_tokens_to_string(self, tokens):
        """Converts a sequence of tokens (string) in a single string."""
        current_sub_tokens = []
        out_string = ""
        prev_is_special = False
        for token in tokens:
            # make sure that special tokens are not decoded using sentencepiece model
            if token in self.all_special_tokens:
                if not prev_is_special:
                    out_string += " "
                out_string += self.sp_model.decode(current_sub_tokens) + token
                prev_is_special = True
                current_sub_tokens = []
            else:
                current_sub_tokens.append(token)
                prev_is_special = False
        out_string += self.sp_model.decode(current_sub_tokens)
        return out_string.strip()

    def build_inputs_with_special_tokens(self, token_ids_0, token_ids_1=None):
        if self.add_bos_token:
            bos_token_ids = [self.bos_token_id]
        else:
            bos_token_ids = []

        output = bos_token_ids + token_ids_0

        if token_ids_1 is not None:
            output = output + token_ids_1

        if self.add_eos_token:
            output = output + [self.eos_token_id]

        return output

    def get_special_tokens_mask(
            self, token_ids_0: List[int], token_ids_1: Optional[List[int]] = None,
            already_has_special_tokens: bool = False
    ) -> List[int]:
        """
        Retrieve sequence ids from a token list that has no special tokens added. This method is called when adding
        special tokens using the tokenizer `prepare_for_model` method.
        Args:
            token_ids_0 (`List[int]`):
                List of IDs.
            token_ids_1 (`List[int]`, *optional*):
                Optional second list of IDs for sequence pairs.
            already_has_special_tokens (`bool`, *optional*, defaults to `False`):
                Whether or not the token list is already formatted with special tokens for the model.
        Returns:
            `List[int]`: A list of integers in the range [0, 1]: 1 for a special token, 0 for a sequence token.
        """
        if already_has_special_tokens:
            return super().get_special_tokens_mask(
                token_ids_0=token_ids_0, token_ids_1=token_ids_1, already_has_special_tokens=True
            )

        if token_ids_1 is None:
            return [1] + ([0] * len(token_ids_0)) + [1]
        return [1] + ([0] * len(token_ids_0)) + [1, 1] + ([0] * len(token_ids_1)) + [1]

    def create_token_type_ids_from_sequences(
            self, token_ids_0: List[int], token_ids_1: Optional[List[int]] = None
    ) -> List[int]:
        """
        Create a mask from the two sequences passed to be used in a sequence-pair classification task. T5 does not make
        use of token type ids, therefore a list of zeros is returned.
        Args:
            token_ids_0 (`List[int]`):
                List of IDs.
            token_ids_1 (`List[int]`, *optional*):
                Optional second list of IDs for sequence pairs.
        Returns:
            `List[int]`: List of zeros.
        """
        eos = [self.eos_token_id]

        if token_ids_1 is None:
            return len(token_ids_0 + eos) * [0]
        return len(token_ids_0 + eos + token_ids_1 + eos) * [0]


class KoalaEntry(ModelServerEntry):
    def __init__(self, model_path) -> None:
        super().__init__()
        self.tokenizer = None
        self.prefix_tokenizer = None
        self.model = None
        self.model_path = model_path

    def inference_koala(self, text, temperature):
        print(text)
        inputs = self.prefix_tokenizer(
            text,
            padding='max_length',
            truncation=True,
            max_length=1024,
            return_tensors='pt',
        ).to(self.model.device)
        print(inputs)
        input_tokens = inputs.input_ids
        input_mask = inputs.attention_mask
        input_tokens[:, 0] = self.tokenizer.bos_token_id
        input_mask[:, 0] = 1

        with torch.no_grad():
            try:
                output = self.model.generate(
                    input_ids=input_tokens,
                    attention_mask=input_mask,
                    max_length=2048,
                    do_sample=True,
                    temperature=temperature
                )[:, input_tokens.shape[1]:]
            except Exception as e:
                print(f"exception inference {e}")
                return [""] * len(text)

        print(output)
        output_text = []
        for text in list(self.tokenizer.batch_decode(output)):
            print(text)
            if self.tokenizer.eos_token in text:
                text = text.split(self.tokenizer.eos_token, maxsplit=1)[0]
            output_text.append(text)
        print(output_text[0])
        print(input_tokens.shape, output.shape)
        return output_text

    def construct_prompt(self, batch: List[List[Dict[str, str]]]) -> List[str]:
        prompts = []
        for item in batch:
            prompt = "BEGINNING OF CONVERSATION: "
            for utter in item:
                if utter["role"] == "user":
                    prompt += " USER: {prompt}".format(prompt=utter["content"])
                elif utter["role"] == "assistant":
                    prompt += " GPT:{prompt}".format(prompt=utter["content"]) + "</s>"
            prompt += " GPT:"
            prompts.append(prompt)
        return prompts

    def activate(self, device: str) -> None:
        vocab_file = "models/tokenizer.model"
        self.prefix_tokenizer = LLaMATokenizer(
            vocab_file=vocab_file,
            add_bos_token=False,
            add_eos_token=False,
            padding_side="left",
            truncation_side="left",
        )
        self.tokenizer = LLaMATokenizer(
            vocab_file=vocab_file,
            add_bos_token=False,
            add_eos_token=False,
            padding_side="right",
            truncation_side="right",
        )
        model = AutoModelForCausalLM.from_pretrained(self.model_path, trust_remote_code=True).half().to(device)
        model = model.eval()
        self.model = model
        print("model and tokenizer loaded")

    def deactivate(self) -> None:
        del self.model
        del self.tokenizer
        del self.prefix_tokenizer
        self.model = None
        self.tokenizer = None
        self.prefix_tokenizer = None
        torch.cuda.empty_cache()
        print("model and tokenizer cleared")

    def inference(self, batch: List[List[Dict[str, str]]], temperature=None) -> List[str]:
        return self.inference_koala(self.construct_prompt(batch), temperature or 0.7)
