from agent import Agent, Session
import openai, anthropic
import google.generativeai as palm
import os

class Gpt_4(Agent):
    def __init__(self) -> None:
        self.key = os.getenv('GPT4_API_KEY')

    def inference(self, history: List[dict]) -> str:
        message = []
        for h in history:
            if h['role'] == 'agent':
                h['role'] = 'assistant'
            message.append(h)
            
        resp = openai.ChatCompletion.create(
            model="gpt-4", 
            messages=message, 
            api_key=self.key, 
            timeout=120
        )
        
        return resp.json()["choices"][0]["message"]["content"]
    
class Gpt_3_5_turbo(Agent):
    def __init__(self) -> None:
        self.key = os.getenv('GPT3-5-TURBO_API_KEY')

    def inference(self, history: List[dict]) -> str:
        message = []
        for h in history:
            if h['role'] == 'agent':
                h['role'] = 'assistant'
            message.append(h)
            
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo", 
            messages=message, 
            api_key=self.key, 
            timeout=120
        )
        
        return resp.json()["choices"][0]["message"]["content"]
    
class Text_davinci_003(Agent):
    def __init__(self) -> None:
        self.key = os.getenv('TEXT-DAVINCI-003_API_KEY')

    def inference(self, history: List[dict]) -> str:
        prompt = ''
        for h in history:
            role = 'Assistant' if h['role'] == 'agent' else h['role']
            content = h['content']
            prompt += f"{role}: {content}\n\n"
        prompt += 'Assistant: '
        
        resp = openai.Completion.create(
            model="text-davinci-003", 
            prompt=prompt,
            max_tokens=2000,
            api_key=self.key, 
            timeout=120
        )
        
        return resp.json()["choices"][0]["text"]
    
class Text_davinci_002(Agent):
    def __init__(self) -> None:
        self.key = os.getenv('TEXT-DAVINCI-002_API_KEY')

    def inference(self, history: List[dict]) -> str:
        prompt = ''
        for h in history:
            role = 'Assistant' if h['role'] == 'agent' else h['role']
            content = h['content']
            prompt += f"{role}: {content}\n\n"
        prompt += 'Assistant: '
        
        resp = openai.Completion.create(
            model="text-davinci-002", 
            prompt=prompt,
            max_tokens=2000,
            api_key=self.key, 
            timeout=120
        )
        
        return resp.json()["choices"][0]["text"]
    
class Claude_v1_3(Agent):
    def __init__(self) -> None:
        self.key = os.getenv('CLAUDE-V1-3_API_KEY')

    def inference(self, history: List[dict]) -> str:
        for h in history:
            if message["role"] == "user":
                prompt += anthropic.HUMAN_PROMPT + message["content"]
            else:
                prompt += anthropic.AI_PROMPT + message["content"]
        prompt += anthropic.AI_PROMPT
        c = anthropic.Client(self.key)
        resp = c.completion(
            prompt=prompt,
            stop_sequences=[anthropic.HUMAN_PROMPT],
            model='claude-v1.3',
            max_tokens_to_sample=2048,
        )
        return resp
    
class Claude_instant_v1_1(Agent):
    def __init__(self) -> None:
        self.key = os.getenv('CLAUDE-INSTANT-V1-1_API_KEY')

    def inference(self, history: List[dict]) -> str:
        for h in history:
            if message["role"] == "user":
                prompt += anthropic.HUMAN_PROMPT + message["content"]
            else:
                prompt += anthropic.AI_PROMPT + message["content"]
        prompt += anthropic.AI_PROMPT
        c = anthropic.Client(self.key)
        resp = c.completion(
            prompt=prompt,
            stop_sequences=[anthropic.HUMAN_PROMPT],
            model='claude-instant-v1.1',
            max_tokens_to_sample=2048,
        )
        return resp
    
class Text_bison_001(Agent):
    def __init__(self) -> None:
        self.key = os.getenv('TEXT-BISON-001_API_KEY')
        palm.configure(api_key=self.key)

    def inference(self, history: List[dict]) -> str:
        for ix, h in enumerate(history):
            if message["role"] == "user":
                prompt += f'## Round {ix // 2 + 1} ##\nUser: {message["content"]}\n'
            else:
                prompt += f'Assistant: {message["content"]}\n\n'
        prompt += f'Assistant: '
        
        resp = palm.generate_text(
            model="models/text-bison-001",
            prompt=prompt,
            temperature=0.7,
            max_output_tokens=2048,
        )
        
        return resp.result.text

# TODO: add chatglm_130b
class Chatglm_130b(Agent):
    def __init__(self) -> None:
        pass

    def create_session(self) -> Session:
        return Session(self.inference)

    def inference(self, history: List[dict]) -> str:
        raise NotImplementedErro
    
if __name__ == '__name__':
    gpt4 = Gpt_4()
    gpt4.inference([{'role': 'user', 'content': 'hello'}])
    gp3_5_turbo = Gpt_3_5_turbo()
    text_davinci_003 = Text_davinci_003()
    text_davinci_002 = Text_davinci_002()
    claude_v1_3 = Claude_v1_3()
    claude_instant_v1_1 = Claude_instant_v1_1()
    palm = Text_bison_001()
    
    