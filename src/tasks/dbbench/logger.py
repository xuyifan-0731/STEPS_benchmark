import datetime
import os
import sys


class MuteStream:
    def write(self, s):
        pass

    def flush(self):
        pass

    def close(self):
        pass


class QuickFlushFileStream:
    def __init__(self, file):
        self.file = file

    def write(self, s):
        self.file.write(s)
        self.file.flush()

    def flush(self):
        self.file.flush()

    def close(self):
        self.file.close()


class ErrorSplittingStream:
    def __init__(self, file, printing):
        self.file = file
        self.printing = printing

    def write(self, s):
        self.file.write(s)
        self.file.flush()
        print(s, file=self.printing, end="")

    def flush(self):
        self.file.flush()

    def close(self):
        self.file.close()


class InteractionLog:
    def __init__(self,
                 root_dir: str = "logs/%s" % (datetime.datetime.now().strftime("%Y-%m-%d=%H-%M-%S")),
                 name: str = "0", flags=0) -> None:
        os.makedirs(root_dir, exist_ok=True)
        self.root_dir = root_dir
        self.name = name
        self.suffix_index = 0
        while os.path.exists(self.file_name):
            self.suffix_index += 1
        self.stdout = None
        self.logfile = None
        self.flags = flags

    @property
    def file_name(self):
        return os.path.join(self.root_dir, "%s-%d.log" % (self.name, self.suffix_index))

    def __enter__(self):
        self.stdout = sys.stdout
        self.stderr = sys.stderr
        self.logfile = QuickFlushFileStream(open(self.file_name, 'w', encoding="utf-8"))
        self.errfile = ErrorSplittingStream(open(self.file_name[:-4] + ".err", "w"), self.stderr)
        sys.stderr = self.errfile
        sys.stdout = self.logfile
        if self.flags & 1:
            sys.stdout = MuteStream()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        sys.stdout = self.stdout
        sys.stderr = self.stderr
        self.logfile.close()
        self.logfile = None
        self.stdout = None
