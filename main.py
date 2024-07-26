import DaVinciResolveScript
from datetime import datetime, timedelta

import tkinter as tk
from tkinter import ttk

from path import PathManager, FilesystemContext
from resolve import ResolveContext, ResolveUpdater
from proxy import ProxyGenerator
from motion import MotionMagnitudeGenerator


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
        self.motion_magnitude_wav_generator = MotionMagnitudeGenerator(
            self.path_manager
        )

    def generate_derived_files(self):
        print("Checking for new derived files to be generated...")
        self.proxy_generator.generate_proxies()
        self.motion_magnitude_wav_generator.generate_motion_wavs()

    def link_rectilinear_proxies(self):
        self.resolve_updater.LinkProxyForAllMediaPoolItemsInCurrentTimeline(
            self.path_manager.slow_proxy_rectilinear_dir_path
        )

    def create_missing_sequences_and_shots_in_resolve(self):
        self.resolve_updater.CreateMissingSequencesAndShotsInResolve()


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
        ttk.Button(
            self,
            text="Create Missing Sequences And Shots In Resolve",
            command=self.delegate.create_missing_sequences_and_shots_in_resolve,
        ).pack(pady=10)
        ttk.Button(self, text="Exit", command=self.quit).pack(pady=10)

        # self.after(5000, self.generate_proxies)
        self.generate_derived_files()

    def button2_click(self):
        print("Button 2 clicked!")

    def generate_derived_files(self):
        self.delegate.generate_derived_files()
        self.after(5000, self.generate_derived_files)


if __name__ == "__main__":
    delegate = AppDelegate()
    app = MyApp(delegate)
    app.mainloop()
