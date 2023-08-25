try:
    from .openai_agents import OpenAIChatCompletion, OpenAICompletion
except:
    print("> [Warning] OpenAI Agents are not available")
try:
    from .claude_agents import Claude
except:
    print("> [Warning] OpenAI Agents are not available")
from .api import APIAgent, APIAgent_claude, APIAgent_completion