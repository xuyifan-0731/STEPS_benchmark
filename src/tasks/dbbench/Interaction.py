import socket
import sys
import time

import docker
import mysql.connector
from docker.models import containers

from logger import InteractionLog


class Container:
    port = 3000

    def __init__(self, volume: str = None, init_file: str = None, image: str = "mysql"):
        self.image = image
        self.client = docker.from_env()
        password = "password"
        print("trying port", file=sys.stderr)
        while self.is_port_open(Container.port):
            Container.port += 1
        self.port = Container.port
        print("port decided", self.port, file=sys.stderr)
        if volume:
            self.container: containers.Container = \
                self.client.containers.run(image,
                                           name=f"mysql_{self.port}",
                                           environment={
                                               "MYSQL_ROOT_PASSWORD": password,
                                               # "MYSQL_DATABASE": database
                                           },
                                           ports={"3306": self.port},
                                           volumes={volume: {"bind": "/var/lib/mysql", "mode": "rw"}},
                                           detach=True, tty=True,
                                           stdin_open=True, remove=True)
        else:
            self.container: containers.Container = \
                self.client.containers.run(image,
                                           name=f"mysql_{self.port}",
                                           environment={
                                               "MYSQL_ROOT_PASSWORD": password,
                                               # "MYSQL_DATABASE": database
                                           },
                                           ports={"3306": self.port},
                                           detach=True, tty=True,
                                           stdin_open=True, remove=True)
        Container.port += 1

        time.sleep(1)

        while True:
            try:
                self.conn = mysql.connector.connect(
                    host="127.0.0.1",
                    user="root",
                    password="password",
                    port=self.port,
                    # database=database
                    pool_reset_session=True,
                )
            except mysql.connector.errors.OperationalError:
                print("sleep", file=sys.stderr)
                time.sleep(1)
            else:
                break

        # self.conn.autocommit = True

        if init_file:
            print(f"Initializing container with {init_file}")
            with open(init_file) as f:
                data = f.read()
            for sql in data.split("\n\n"):
                try:
                    self.execute(sql, verbose=False)
                except Exception as e:
                    print(e)

        self.deleted = False

    def delete(self):
        self.conn.close()
        self.container.stop()
        self.deleted = True

    def __del__(self):
        if not self.deleted:
            self.delete()

    def execute(self, sql: str, database: str = None, truncate: bool = True, verbose: bool = True,
                no_except: bool = False) -> [str | None]:
        if verbose:
            print("== EXECUTING ==")
            if len(sql) < 300:
                print(sql)
        self.conn.reconnect()
        try:
            with self.conn.cursor() as cursor:
                if database:
                    cursor.execute(f"use `{database}`;")
                    cursor.fetchall()
                cursor.execute(sql, multi=True)
                result = cursor.fetchall()
                result = str(result)
            self.conn.commit()
        except Exception as e:
            if no_except:
                raise
            result = str(e)
        if verbose:
            if len(result) < 200:
                print(result)
            else:
                print("len result:", len(result))
        if len(result) > 800 and truncate:
            result = result[:800] + "[TRUNCATED]"
        if not sql.lower().startswith("select"):
            pass    # IMPORTANT: if `execute` is called in a high rate, here must wait for the transaction
            # time.sleep(0.5)     # insure transaction is done
        return result

    @staticmethod
    def is_port_open(port) -> bool:
        # Create a socket object
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            # Try to connect to the specified port
            sock.connect(('localhost', port))
            # If the connection succeeds, the port is occupied
            return True
        except ConnectionRefusedError:
            # If the connection is refused, the port is not occupied
            return False
        finally:
            # Close the socket
            sock.close()
