from __future__ import annotations
from dataclasses import dataclass, field
from dataclass_wizard import JSONSerializable, property_wizard
from enum import Enum
from typing import Optional, List, Dict

@dataclass
class BaseConfig(JSONSerializable, metaclass=property_wizard):
    name: str  # Task name
    path: str  # task data path relative to DATA_PATH

    module: Optional[str] = None  # Custom task module file, optional
    metrics: List[str] = field(default_factory=lambda: ["ACC", "BLEU", "ROUGE"])  # Evaluation metrics
    save_prediction: bool = True
    save_evaluation: bool = True
    file_pattern: str | Dict[str, str] = "**/*.json*"  # Organize data file in groups

    workers: int = 1
    prompt: str = None
    cot: str = None # default means add cot prompt in the end (e.g. let's think step by step)
    shot: int = 0 # deprecated
    max_length: int = 1024 # change to 2048 if neccessary
    language: str = "en" # support en or cn

    acc_type: str = "EM" # MUL MATHQA EM RE different settings when calculate accuracy
    extract_answer: bool = True # whether to perform second stage
    extract_template: str = None # to extract answer using RE; only valid when choose acc_type == RE
