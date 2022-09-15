from typing import Tuple
from pystray import MenuItem
import pystray
import PIL.Image
from logic import WatcherThread, CrawlWorkerThread
from configparser import ConfigParser
from tkinter import *
from queue import Queue
from threading import Event
from tkui import EditableList


class App(Tk):
    def __init__(self):
        super().__init__()

        self.indexes: list[Tuple[str, WatcherThread,
                                 CrawlWorkerThread, Queue, Event]] = []
        self.indexing_paths: list[str] = []

        self.read_config()
        self.start_threads()

        self.build_ui()

        self.title("undupli")
        self.geometry("700x350")
        self.iconbitmap('favicon.ico')

        self.protocol('WM_DELETE_WINDOW', self.hide_window)

    def read_config(self):
        self.app_config = ConfigParser()
        self.app_config.read('config.ini')
        self.indexing_paths = self.app_config.get(
            "main", "indexingpaths").split("\n")

    def write_config(self):
        with open("config.ini", "w") as f:
            self.app_config.write(f)

    def start_threads(self):
        for _, _, _, _, i_stop in self.indexes:
            i_stop.set()
        self.indexes = []
        for i_path in self.indexing_paths:
            i_queue = Queue()
            i_stop = Event()
            i_watcher = WatcherThread(i_path, i_queue, i_stop)
            i_crawler = CrawlWorkerThread(i_path, i_queue, i_stop)
            i_watcher.start()
            i_crawler.start()
            self.indexes.append(
                (i_path, i_watcher, i_crawler, i_queue, i_stop))

    def stop_threads(self):
        for _, _, _, _, i_stop in self.indexes:
            i_stop.set()
        self.indexes = []

    def build_ui(self):
        self.ui_indexing_path_editlist = EditableList(
            self, item_list=self.indexing_paths)
        self.ui_indexing_path_editlist.place(x=0, y=0, relwidth=1, relheight=1)

    def quit_window(self, icon: pystray.Icon, item: str):
        self.write_config()
        icon.stop()
        self.destroy()

    def show_window(self, icon: pystray.Icon, item: str):
        icon.stop()
        self.after(0, self.deiconify)

    def hide_window(self):
        self.withdraw()
        menu = (MenuItem('Quit', self.quit_window),
                MenuItem('Show', self.show_window))
        favicon = PIL.Image.open("favicon.ico")
        icon = pystray.Icon("name", favicon, "undupli", menu)
        icon.run()


if __name__ == "__main__":
    app = App()
    app.mainloop()
