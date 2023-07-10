import re
import string
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
from typing import *

import numpy as np

from evaluation import (
    GenerationTask,
)


class ExampleTask(GenerationTask):
    @property
    def metrics(self) -> Dict[str, Callable]:
        return {"acc": self.check_acc}

    def check_acc(self, predictions, ground_truths):
        acc = []
        for prediction, ground_truth in zip(predictions, ground_truths):
            try:
                import pdb
                pdb.set_trace()
                if ground_truth[0]["targets"][0] in prediction:
                    acc.append(1)
                else:
                    acc.append(0)
            except:
                acc.append(0)
        acc = np.mean(acc)
        return acc
