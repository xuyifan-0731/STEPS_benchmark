from typing import Callable, Dict, List, Tuple, Any

from .Interaction import Container
import json
from src.task import Task, Dataset, DataPiece, Session


class DBBench(Task[Dict, Dict[str, Any], str]):
    def __init__(self, **configs):
        super().__init__(**configs)
        self.data_file = configs.pop("data_file")
        self.max_round = configs.pop("max_round", 5)
        self.container = Container()
        self.conn = self.container.conn

    def escape(self, string: str, conn=None):
        conn = conn or self.conn
        if type(string) is not str:
            string = str(string)
        return conn._cmysql.escape_string(string).decode("utf-8")

    def get_data(self) -> Dataset[Dict, str]:
        dataset = Dataset()
        with open(self.data_file) as f:
            if self.data_file.endswith("json"):
                data = json.loads(f.read())
            else:
                data = [json.loads(line) for line in f.readlines()]

        for entry in data:
            if entry["type"][0] in ("INSERT", "DELETE", "UPDATE"):
                ans = entry.pop("answer_md5")
            else:
                ans = entry.pop("label")
            inp = entry
            dataset.append(DataPiece(inp, ans))

        return dataset

    def build_sql(self, entry, conn):
        name = entry["table"]["table_name"]
        columns = ",".join(
            [f"`{self.escape(column['name'], conn)}` TEXT" for column in entry["table"]["table_info"]["columns"]])
        column_names = ",".join(
            [f"`{self.escape(column['name'], conn)}`" for column in entry["table"]["table_info"]["columns"]])
        items = []
        for row in entry["table"]["table_info"]["rows"]:
            item = "("
            for col in row:
                item += f"'{self.escape(col, conn)}',"
            item = item[:-1] + ")"
            items.append(item)
        items = ",".join(items)
        sql = f"""CREATE DATABASE IF NOT EXISTS `{name}`;
USE `{name}`;
CREATE TABLE IF NOT EXISTS `{name}` ({columns});
INSERT INTO `{name}` ({column_names}) VALUES {items}; 
COMMIT;
"""
        return sql

    def predict_single(self, session: Session, data_item: Dict) -> Dict[str, Any]:
        container = Container()
        entry = data_item
        # container = self.container
        init = self.build_sql(entry, container.conn)
        container.execute(init)
        db = entry['table']['table_name']
        prompt = entry["description"] + "\n" + entry["add_description"]
        session.inject({"role": "user", "content": prompt})
        res = session.action()
        res = json.loads(res)
        rounds = 0
        try:
            while res and "commit" not in res and rounds < self.max_round:
                if "sql" not in res or not res["sql"]:
                    answer = ""
                    break
                response = container.execute(res["sql"], db)
                if response:
                    session.inject({"role": "user", "content": response})
                else:
                    session.inject({"role": "user", "content": ""})
                res = session.action()
                res = json.loads(res)
                rounds += 1
            else:
                if res:
                    answer = res["commit"]
                else:
                    answer = ""
        except Exception as e:
            # TODO: log exception
            answer = ""
        if data_item["type"][0] in ("INSERT", "DELETE", "UPDATE"):
            columns = ",".join([f"`{self.escape(column['name'], container.conn)}`"
                                for column in entry["table"]["table_info"]["columns"]])
            md5_query = f"select md5(group_concat(rowhash order by rowhash)) as hash " \
                        f"from( SELECT substring(MD5(CONCAT_WS(',', {columns})), 1, 5) AS rowhash FROM `{db}`) as sub;"
            # md5 = entry["answer_md5"]
            answer = container.execute(md5_query, db)
        container.execute(f"drop database `{db}`")
        return {
            "answer": str(answer),
            "type": entry["type"][0],
            "history": session.history
        }

    @property
    def metrics(self) -> Dict[str, Callable[[List[Dict[str, Any]], List[str]], float]]:
        def factory(typ):
            def acc(inp: List[Dict[str, Any]], tar: List[str]) -> float:
                correct = 0
                total = 0
                for tmp, cor in zip(inp, tar):
                    if not tmp:
                        total += 1
                        continue
                    ans, t = tmp["answer"], tmp["type"]
                    if t != typ:
                        continue
                    if t in ("INSERT", "DELETE", "UPDATE"):
                        correct += ans == t
                    else:
                        correct += set(eval(ans)) == set(eval(t))
                    total += 1
                return correct / total

            return acc

        types = ['other', 'counting', 'comparison', 'ranking', 'aggregation-SUM', 'aggregation-MIN', 'aggregation-MAX',
                 'aggregation-AVG', 'INSERT', 'DELETE', 'UPDATE']

        ret = {}
        for typ in types:
            ret[typ + "_accuracy"] = factory(typ)
        ret["all"] = factory(None)

        return ret
