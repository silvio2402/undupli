from msilib.schema import Error
from threading import Thread
import os
import hashlib

import win32file
import win32con

DIRECTORYCHANGEACTIONS = {
    1: "Created",
    2: "Deleted",
    3: "Updated",
    4: "Renamed from something",
    5: "Renamed to something"
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
    def __init__(self, watch_path: str) -> None:
        super().__init__()

        self.watch_path = watch_path

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
            for action, file in results:
                full_filename = os.path.join(self.watch_path, file)
                print(full_filename, DIRECTORYCHANGEACTIONS.get(action, "Unknown"))


def crawl(crawl_path: str) -> dict:
    out_dict = dict()
    for path in os.listdir(crawl_path):
        abs_path = os.path.join(crawl_path, path)
        if os.path.isdir(abs_path):
            try:
                out_dict[path] = crawl(abs_path)
                print("dir", abs_path)
            except Exception as e:
                print(e)
        elif os.path.isfile(abs_path):
            try:
                stat_result = os.stat(abs_path)
                if stat_result.st_file_attributes & FILE_ATTRIBUTE["RECALL_ON_DATA_ACCESS"]:
                    print("file", abs_path, "remote")
                    continue  # skip non-local files
                if stat_result.st_size > 1024**3:
                    continue  # skip files > 1GB
                with open(abs_path, 'rb') as f:
                    md5 = hashlib.md5()
                    while True:
                        chunk = f.read(1024*64)  # read 64kB chunks
                        if not chunk:
                            break
                        md5.update(chunk)

                out_dict[path] = md5.digest()
                print("file", abs_path, "hash", md5.hexdigest())
            except Exception as e:
                print(e)
        else:
            print("unknown", abs_path)
    return out_dict


class IndexerThread(Thread):
    def __init__(self) -> None:
        super().__init__()

    def run(self) -> None:
        pass


def print_st_file_attributes(st_file_attributes):
    print({
        "readonly": st_file_attributes & 0x1,
        "hidden": st_file_attributes & 0x2,
        "system": st_file_attributes & 0x4,
        "directory": st_file_attributes & 0x10,
        "archive": st_file_attributes & 0x20,
        "device": st_file_attributes & 0x40,
        "normal": st_file_attributes & 0x80,
        "temporary": st_file_attributes & 0x100,
        "sparse_file": st_file_attributes & 0x200,
        "reparse_point": st_file_attributes & 0x400,
        "compressed": st_file_attributes & 0x800,
        "offline": st_file_attributes & 0x1000,
        "not_content_indexed": st_file_attributes & 0x2000,
        "encrypted": st_file_attributes & 0x4000,
        "integrity_stream": st_file_attributes & 0x8000,
        "virtual": st_file_attributes & 0x10000,
        "no_scrub_data": st_file_attributes & 0x20000,
        "recall_on_open": st_file_attributes & 0x40000,
        "pinned": st_file_attributes & 0x80000,
        "unpinned": st_file_attributes & 0x100000,
        "recall_on_data_access": st_file_attributes & 0x400000,
    })


if __name__ == "__main__":
    # stat = os.stat('C:\\Users\\silvi\\OneDrive\\Dokumente\\Default.rdp',
    #                follow_symlinks=False)
    # print(stat)
    # print_st_file_attributes(stat.st_file_attributes)

    # watchThr = WatcherThread('.')
    # watchThr.start()

    crawl('C:\\Users\\silvi\\OneDrive\\Dokumente')
