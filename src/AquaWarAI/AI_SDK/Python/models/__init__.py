from .chatgpt import chatgpt_call
from .chatglm import chatglm_call
from .gpt4 import gpt4_call
from .claude import claude_call
from .vicuna import vicuna_call
from .palm import palm_call

model_call = {
    'chatgpt': chatgpt_call,
    'chatglm': chatglm_call,
    'gpt4': gpt4_call,
    'claude': claude_call,
    'vicuna': vicuna_call,
    'palm': palm_call
}