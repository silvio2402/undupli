import queue
from threading import Thread, Event
import os
import hashlib
import time
from types import NoneType

import win32file
import win32con


DIRECTORY_CHANGE_ACTIONS = {
    "CREATED": 1,
    "DELETED": 2,
    "UPDATED": 3,
    "RENAMED_FROM": 4,
    "RENAMED_TO": 5
}
# Thanks to Claudio Grondi for the correct set of numbers
FILE_LIST_DIRECTORY = 0x0001

FILE_ATTRIBUTE = {
    "READONLY": 0x1,
    "HIDDEN": 0x2,
    "SYSTEM": 0x4,
    "DIRECTORY": 0x10,
    "ARCHIVE": 0x20,
    "DEVICE": 0x40,
    "NORMAL": 0x80,
    "TEMPORARY": 0x100,
    "SPARSE_FILE": 0x200,
    "REPARSE_POINT": 0x400,
    "COMPRESSED": 0x800,
    "OFFLINE": 0x1000,
    "NOT_CONTENT_INDEXED": 0x2000,
    "ENCRYPTED": 0x4000,
    "INTEGRITY_STREAM": 0x8000,
    "VIRTUAL": 0x10000,
    "NO_SCRUB_DATA": 0x20000,
    "RECALL_ON_OPEN": 0x40000,
    "PINNED": 0x80000,
    "UNPINNED": 0x100000,
    "RECALL_ON_DATA_ACCESS": 0x400000,
}


class WatcherThread(Thread):
    def __init__(self, watch_path: str, queue: queue.Queue, stop_event: Event) -> None:
        super().__init__()

        self.watch_path = os.path.abspath(watch_path)
        self.queue = queue
        self.stop_event = stop_event

        self.h_dir = win32file.CreateFile(
            self.watch_path,
            FILE_LIST_DIRECTORY,
            win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE | win32con.FILE_SHARE_DELETE,
            None,
            win32con.OPEN_EXISTING,
            win32con.FILE_FLAG_BACKUP_SEMANTICS,
            None
        )

    def run(self) -> None:
        while True:
            if self.stop_event.is_set():
                return
            #
            # ReadDirectoryChangesW takes a previously-created
            # handle to a directory, a buffer size for results,
            # a flag to indicate whether to watch subtrees and
            # a filter of what changes to notify.
            #
            # NB Tim Juchcinski reports that he needed to up
            # the buffer size to be sure of picking up all
            # events when a large number of files were
            # deleted at once.
            #
            results = win32file.ReadDirectoryChangesW(
                self.h_dir,
                1024,
                True,
                win32con.FILE_NOTIFY_CHANGE_FILE_NAME |
                win32con.FILE_NOTIFY_CHANGE_DIR_NAME |
                win32con.FILE_NOTIFY_CHANGE_ATTRIBUTES |
                win32con.FILE_NOTIFY_CHANGE_SIZE |
                win32con.FILE_NOTIFY_CHANGE_LAST_WRITE |
                win32con.FILE_NOTIFY_CHANGE_SECURITY,
                None,
                None
            )
            files = set()
            for action, file in results:
                full_filename = os.path.abspath(os.path.join(
                    self.watch_path, file))
                if file not in files:
                    self.queue.put(full_filename)
                    files.add(file)
                # print(full_filename, action)


def crawl(crawl_path: str) -> dict:
    out_dict = dict()
    if os.path.isdir(crawl_path):
        # print(os.listdir(crawl_path))
        for path in os.listdir(crawl_path):
            abs_path = os.path.join(crawl_path, path)
            try:
                out_dict[path] = crawl(abs_path)
                # print("dir", abs_path)
            except Exception as e:
                print(e)
    elif os.path.isfile(crawl_path):
        try:
            stat_result = os.stat(crawl_path)
            # print(stat_result.st_size)
            out_dict["*st_size"] = stat_result.st_size
            if stat_result.st_file_attributes & FILE_ATTRIBUTE["RECALL_ON_DATA_ACCESS"]:
                # print("file", crawl_path, "remote")
                return out_dict  # skip non-local files
            if stat_result.st_size > 1024**3:
                return out_dict  # skip files > 1GB
            with open(crawl_path, 'rb') as f:
                md5 = hashlib.md5()
                while True:
                    chunk = f.read(1024*64)  # read 64kB chunks
                    if not chunk:
                        break
                    md5.update(chunk)

            out_dict["*hash_md5"] = md5.hexdigest()
            # print("file", crawl_path, "hash", md5.hexdigest())
        except Exception as e:
            print(e)
    else:
        print("unknown", crawl_path)
        return None
    return out_dict


def splitpath(path):
    allparts = []
    while 1:
        parts = os.path.split(path)
        if parts[0] == path:  # sentinel for absolute paths
            allparts.insert(0, parts[0])
            break
        elif parts[1] == path:  # sentinel for relative paths
            allparts.insert(0, parts[1])
            break
        else:
            path = parts[0]
            allparts.insert(0, parts[1])
    return allparts


def update_crawl_index(ci_path: str, ci: dict, new_ci_path: str, new_ci: dict):
    new_path_segments = splitpath(os.path.abspath(new_ci_path))[
        len(splitpath(os.path.abspath(ci_path))):]

    out_dict = ci
    repl = out_dict
    for seg in new_path_segments[:-1]:
        repl = repl[seg]
    repl[new_path_segments[-1]] = new_ci

    return out_dict


class CrawlWorkerThread(Thread):
    def __init__(self, crawl_path: str, crawl_queue: queue.Queue, stop_event: Event) -> None:
        super().__init__()

        self.crawl_path = os.path.abspath(crawl_path)
        self.crawl_queue = crawl_queue
        self.stop_event = stop_event

        self.file_index = dict()
        self.last_indexed: NoneType | float = None

    def run(self) -> None:
        while True:
            if self.stop_event.is_set():
                return

            if not self.last_indexed or time.time() - self.last_indexed > 60*60*2:
                with self.crawl_queue.mutex:
                    self.file_index = crawl(self.crawl_path)
                    print("done routine crawl", self.crawl_path)
                    self.last_indexed = time.time()
                    self.crawl_queue.queue.clear()
            try:
                crawl_item: str = self.crawl_queue.get(block=False)
                self.file_index = update_crawl_index(
                    self.crawl_path, self.file_index, crawl_item, crawl(crawl_item))
                print("done crawl", crawl_item)
            except queue.Empty:
                pass


if __name__ == "__main__":
    pass
