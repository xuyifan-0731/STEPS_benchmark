from .local_agent import LocalAgent
from .do_nothing_agent import DoNothingAgent
# from .fastchat_client import FastChatAgent
# from .llm_agent import *
try:
    from .local import *
except:
    print("> [Warning] Local agent not available")
try:
    from .fastchat_client import FastChatAgent
except:
    print("> [Warning] FastChat agent not available")
try:
    from .api_agents import *
except:
    print("> [Warning] API agents not available")
try:
    from .http_agent import HTTPAgent
except:
    print("> [Warning] HTTP agent not available")

# from .chatglm import *