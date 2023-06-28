import multiprocessing
import traceback

from mysql.connector import MySQLConnection, CMySQLConnection
from mysql.connector.pooling import PooledMySQLConnection

from Agent import *
from Interaction import *
from logger import InteractionLog

conn: PooledMySQLConnection | MySQLConnection | CMySQLConnection | None = None

agent_exec = ""
MAX_ROUND = 5


def escape(string: str):
    if type(string) is not str:
        string = str(string)
    return conn._cmysql.escape_string(string).decode("utf-8")


def build_sql(entry):
    name = entry["table"]["table_name"]
    columns = ",".join([f"`{escape(column['name'])}` TEXT" for column in entry["table"]["table_info"]["columns"]])
    column_names = ",".join([f"`{escape(column['name'])}`" for column in entry["table"]["table_info"]["columns"]])
    items = []
    for row in entry["table"]["table_info"]["rows"]:
        item = "("
        for col in row:
            item += f"'{escape(col)}',"
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


def judge(entry: dict, agent: Agent, container=None) -> bool:
    container = container or Container()
    init = build_sql(entry)
    container.execute(init)
    db = entry['table']['table_name']
    prompt = entry["description"] + "\n" + entry["add_description"]
    print(prompt)
    agent.message(prompt)
    correct = set(entry["label"])
    res = agent.act()
    rounds = 0
    while res and "commit" not in res:
        if "sql" not in res or not res["sql"] or rounds >= MAX_ROUND:
            answer = None
            break
        response = container.execute(res["sql"], db)
        if response:
            agent.message(response)
        else:
            agent.message("")
        res = agent.act()
        rounds += 1
    else:
        if res:
            answer = set(res["commit"])
        else:
            answer = None
    print("Answer:", answer)
    print("Correct:", correct)
    # container.delete()
    container.execute(f"drop database `{db}`")
    return answer == correct


def judge_operate(entry, agent, container=None):
    container = container or Container()
    init = build_sql(entry)
    container.execute(init)
    columns = ",".join([f"`{escape(column['name'])}`" for column in entry["table"]["table_info"]["columns"]])
    db = entry['table']['table_name']
    md5_query = f"select md5(group_concat(rowhash order by rowhash)) as hash " \
                f"from( SELECT substring(MD5(CONCAT_WS(',', {columns})), 1, 5) AS rowhash FROM `{db}`) as sub;"
    md5 = entry["answer_md5"]
    prompt = entry["description"] + "\n" + entry["add_description"]
    print(prompt)
    agent.message(prompt)
    res = agent.act()
    rounds = 0
    while res and "commit" not in res and rounds < MAX_ROUND:
        if "sql" not in res or not res["sql"]:
            break
        response = container.execute(res["sql"], db)
        if response:
            agent.message(response)
        else:
            agent.message("")
        res = agent.act()
        rounds += 1
    answer = container.execute(md5_query, db)
    # container.delete()
    # correct.delete()
    container.execute(f"drop database `{db}`")
    print("Answer:", answer)
    print("Correct:", md5)
    return answer == md5


def worker(log_dir: str, entries: list[dict], idx: int, description: str = ""):
    results = []
    with InteractionLog(log_dir, str(idx)):
        print(f"Worker {idx} judging {len(entries)} entries.")
        print(f"Description:", description)
        c1 = Container()
        global conn
        if not conn:
            conn = c1.conn
        for i, entry in enumerate(entries):
            print(f"=== Judging {i} ===")
            print(i, file=sys.stderr)
            try:
                agent = eval(agent_exec)
                if entry["type"][0] in ("INSERT", "DELETE", "UPDATE"):
                    res = judge_operate(entry, agent, c1)
                else:
                    res = judge(entry, agent, c1)
                results.append(res)
                print(f"### {i} Result: {res}")
            except Exception as e:
                print("Judge Failed With Error")
                print(e)
                traceback.print_exc()
        print("Final Result:", sum(results) / len(results))


def evaluate(file: str, num_worker: int = 5):
    with open(file) as f:
        if file.endswith("json"):
            data = json.loads(f.read())
        elif file.endswith("jsonl"):
            data = [json.loads(line) for line in f.readlines()]
        else:
            raise ValueError(f"Unknown file type: {file}")

    segment = len(data) // num_worker
    log_dir = "logs/%s" % (datetime.datetime.now().strftime("%Y-%m-%d=%H-%M-%S"))

    if num_worker > 1:
        processes = []
        for i in range(num_worker):
            start, end = (i * segment, (i + 1) * segment if i < num_worker - 1 else len(data))
            p = multiprocessing.Process(target=worker, args=(
                log_dir, data[start:end], i, f"ranging: {(start, end)}"))
            processes.append(p)
            p.start()
            time.sleep(1)

        for p in processes:
            p.join()
    else:
        worker(log_dir, data, 0, "Single Worker")


if __name__ == '__main__':
    agent_exec = input(">>> ")
    print("Got Agent EXEC:", agent_exec)
    evaluate("data/sample5.jsonl", 3)
