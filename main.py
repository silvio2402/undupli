from tkinter import *
from pystray import MenuItem
import pystray
from PIL import Image


class App(Tk):
    def __init__(self):
        super().__init__()

        self.title("undupli")
        self.geometry("700x350")
        self.iconbitmap('favicon.ico')

        self.protocol('WM_DELETE_WINDOW', self.hide_window)

    def quit_window(self, icon: pystray.Icon, item: str):
        icon.stop()
        self.destroy()

    def show_window(self, icon: pystray.Icon, item: str):
        icon.stop()
        self.after(0, self.deiconify())

    def hide_window(self):
        self.withdraw()
        menu = (MenuItem('Quit', self.quit_window),
                MenuItem('Show', self.show_window))
        favicon = Image.open("favicon.ico")
        icon = pystray.Icon("name", favicon, "undupli", menu)
        icon.run()


if __name__ == "__main__":
    app = App()
    app.mainloop()
