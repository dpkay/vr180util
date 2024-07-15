import DaVinciResolveScript
from datetime import datetime, timedelta

import tkinter as tk
from tkinter import ttk

from path import PathManager, FilesystemContext
from resolve import ResolveContext, ResolveUpdater
from proxy import ProxyGenerator


class AppDelegate:
    def __init__(self):
        SLOW_WORK_DIR = r"g:\vr180_work"
        FAST_WORK_DIR = r"c:\vr180_work_fast"
        self.path_manager = PathManager(
            slow_work_dir_path=SLOW_WORK_DIR, fast_work_dir_path=FAST_WORK_DIR
        )
        self.resolve_context = ResolveContext(DaVinciResolveScript.scriptapp("Resolve"))
        self.filesystem_context = FilesystemContext(self.path_manager)
        self.resolve_updater = ResolveUpdater(
            self.resolve_context, self.filesystem_context
        )
        self.proxy_generator = ProxyGenerator(self.path_manager)

    def generate_proxies(self):
        print("Checking for new proxies to be generated...")
        self.proxy_generator.generate_proxies()

    def link_rectilinear_proxies(self):
        self.resolve_updater.LinkProxyForAllMediaPoolItemsInCurrentTimeline(
            self.path_manager.slow_proxy_rectilinear_dir_path
        )


class MyApp(tk.Tk):

    def __init__(self, delegate):
        self.delegate = delegate
        super().__init__()
        self.title("Button Example")

        ttk.Button(
            self,
            text="Link rectilinear proxies for current timeline",
            command=self.delegate.link_rectilinear_proxies,
        ).pack(pady=10)
        ttk.Button(self, text="Button 2", command=self.button2_click).pack(pady=10)
        ttk.Button(self, text="Exit", command=self.quit).pack(pady=10)

        self.after(5000, self.generate_proxies)

    def button2_click(self):
        print("Button 2 clicked!")

    def generate_proxies(self):
        self.delegate.generate_proxies()
        self.after(5000, self.generate_proxies)


if __name__ == "__main__":
    delegate = AppDelegate()
    app = MyApp(delegate)
    app.mainloop()
