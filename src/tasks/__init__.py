from .example_task import ExampleTask
from .humaneval_x import HumanEvalXGenerationTask, HumanEvalXTranslationTask

try:
    from .mbpp import MBPPTask
except:
    print("> [Warning] MBPPTask Import Failed")
try:
    from .tool_execution import ToolExecution
except:
    print("> [Warning] ToolExecution Import Failed")
try:
    from .single_round_tasks import *
except:
    print("> [Warning] Single Round Tasks Import Failed")
try:
    from .composite_task import CompositeTask
except:
    print("> [Warning] CompositeTask Import Failed")
try:
    from .apibench import Apibench
except:
    print("> [Warning] Apibench Import Failed")
try:
    from .os_interaction import OSInteraction
except:
    print("> [Warning] OSInteraction Import Failed")
