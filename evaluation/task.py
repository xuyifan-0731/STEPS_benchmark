from .agent import Agent, Session


class TaskConfig:
    pass


class Task:
    def evaluate(self, agent: Agent):
        raise NotImplementedError

    def predict_all(self, agent: Agent, dataset):
        pass

    def predict_single(self, session: Session, data):
        raise NotImplementedError
