from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

tokenizer = None
model = None

def vicuna_call(history, query, system=None, lan='en'):
    global tokenizer, model
    # init model and tokenizer
    if not tokenizer or not model:
        tokenizer = AutoTokenizer.from_pretrained("/workspace/xuyifan/checkpoints/vicuna/13B", use_fast=False, padding_side="left")
        model = AutoModelForCausalLM.from_pretrained("/workspace/xuyifan/checkpoints/vicuna/13B").cuda().eval()
    
    prompt = ''
    if system:
        if lan == 'en':
            prompt += f'### Human: {system}\n### Assistant: Okay, I will play the game with you according to the rules.</s>'
        else:
            prompt += f'### Human: {system}\n### Assistant: 好的，我会按照规则和你进行游戏</s>'
    
    for ix, chat in enumerate(history):
        prompt += f'### Human: {chat[0]}\n### Assistant: {chat[1]}</s>'
    
    prompt += f'### Human: {query}\n### Assistant: '
    
    inputs = tokenizer(prompt, return_tensors="pt")
    input_len = inputs.input_ids.shape[1]

    with torch.no_grad():
        output_ids = model.generate(
            torch.as_tensor(inputs.input_ids).to('cuda'),
            do_sample=True, temperature=0.7, max_new_tokens=512,
        )
    
    outputs = tokenizer.decode(output_ids[0][input_len:], skip_special_tokens=True)
    
    outputs = outputs.replace('\\', '')
    
    return outputs

