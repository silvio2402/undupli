from tkinter import *
from typing import Tuple


class EditableList(Frame):
    def __init__(self, parent, item_list=[]):
        Frame.__init__(self, parent)

        self.item_list: list[str] = item_list
        self.entries: list[Tuple[Entry, str]] = []
        self.update()

    def update(self) -> None:
        if [item for _, item in self.entries[:-1]] != self.item_list:
            for i, item in enumerate(self.item_list):
                try:
                    entry_item = self.entries[i]
                    if item != entry_item[1]:
                        entry_item[0].delete(0)
                        entry_item[0].insert(0, item)
                except IndexError:
                    new_entry = Entry(self)
                    new_entry.insert(0, item)
                    new_entry.grid(row=i)
                    self.entries.append((new_entry, item))
            if len(self.item_list) < len(self.entries):
                for i in range(len(self.item_list), len(self.entries)-1):
                    self.entries[i][0].destroy()
            self.entries.append((Entry(self), ""))
            self.entries[-1][0].grid(row=len(self.entries)-1)

        return super().update()
