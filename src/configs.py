from __future__ import annotations
from dataclass_wizard import YAMLWizard
from dataclasses import dataclass, field


@dataclass
class YAMLConfig(YAMLWizard):
    module: str = None  # Agent module
    parameters: dict = field(default_factory=dict)  # Agent parameters

    def create(self):
        path = ".".join(self.module.split(".")[:-1])
        mod = __import__(path, fromlist=[self.module.split(".")[-1]])
        return getattr(mod, self.module.split(".")[-1])(**self.parameters)

    @classmethod
    def create_from_yaml(cls, yaml_path: str):
        config = cls.from_yaml_file(yaml_path)
        return config.create()
