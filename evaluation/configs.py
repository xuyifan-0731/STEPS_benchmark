from __future__ import annotations
from dataclass_wizard import YAMLWizard
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict


class TaskType(Enum):
    MULTICHOICE = "mul"
    GENERATION = "gen"
    LANGUAGE_MODEL = "lm"
    OTHER = "other"


@dataclass
class BaseConfig(YAMLWizard):
    name: str  # Task name
    type: TaskType  # Task type
    path: str  # task data path relative to DATA_PATH

    company: str = None
    module: Optional[str] = None  # Custom task module file, optional
    metrics: List[str] = field(default_factory=list)  # Evaluation metrics
    save_prediction: bool = True
    save_evaluation: bool = True
    file_pattern: str | Dict[str, str] = "**/*.json*"  # Organize data file in groups

    workers: int = 1
    timeout: int = 180
    retries: int = 3

    prompt: str = None
    shot: int = 0
    max_length: int = 512 # 2048 words
    language: str = "en"

    cot: Optional[str] = None

    #def __post_init__(self):
        #pass


@dataclass
class MultiChoiceTaskConfig(BaseConfig):
    module = "evaluation.MultiChoiceTask"
    metrics: List[str] = field(default_factory=lambda: ["ACC"])


@dataclass
class GenerationTaskConfig(BaseConfig):
    module = "evaluation.GenerationTask"
    metrics: List[str] = field(default_factory=lambda: ["ACC", "BLEU", "ROUGE"])

@dataclass
class LanguageModelTaskConfig(BaseConfig):
    module = "evaluation.LanguageModelTask"
    metrics: List[str] = field(default_factory=lambda: ["PPL"])
