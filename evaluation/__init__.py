from .agent import *
from .task import *
from .configs import *
from .tasks import BaseTask, GenerationTask
from .dataset import EvaluationDataset,GenerationTaskDataset
from .utils import print_rank_0

DEFAULT_CLASS = {
    TaskType.GENERATION: GenerationTask,
}
