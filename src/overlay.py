import tkinter as tk
import threading
from utils.window import move_window_to_foreground
from loot_filter import run_loot_filter
from version import __version__
from utils.process_handler import kill_thread
from logger import Logger
import logging


class ListboxHandler(logging.Handler):
    def __init__(self, listbox):
        logging.Handler.__init__(self)
        self.listbox = listbox

    def emit(self, record):
        log_entry = self.format(record)
        padded_text = " " * 1 + log_entry + " " * 1
        self.listbox.insert(tk.END, padded_text)
        self.listbox.yview(tk.END)  # Auto-scroll to the end


class Overlay:
    def __init__(self):
        self.loot_filter_thread = None
        self.is_minimized = True
        self.root = tk.Tk()
        self.root.title("LootFilter Overlay")
        self.root.attributes("-alpha", 0.8)
        self.root.overrideredirect(True)
        # self.root.wm_attributes("-transparentcolor", "white")
        self.root.wm_attributes("-topmost", True)

        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()
        self.initial_height = int(30)
        self.initial_width = int(self.screen_width * 0.18)
        self.maximized_height = int(160)

        self.canvas = tk.Canvas(self.root, bg="black", height=self.initial_height, width=self.initial_width, highlightthickness=0)
        self.root.geometry(f"{self.initial_width}x{self.initial_height}+{self.screen_width//2 - self.initial_width//2}+0")
        self.canvas.pack()

        self.toggle_button = tk.Button(self.root, text="toggle", bg="#222222", fg="#555555", borderwidth=0, command=self.toggle_size)
        self.canvas.create_window(28, 15, window=self.toggle_button)

        self.filter_button = tk.Button(self.root, text="filter", bg="#222222", fg="#555555", borderwidth=0, command=self.filter_items)
        self.canvas.create_window(70, 15, window=self.filter_button)

        self.terminal_listbox = tk.Listbox(
            self.canvas,
            bg="black",
            fg="white",
            highlightcolor="white",
            highlightthickness=0,
            selectbackground="#222222",
            activestyle=tk.NONE,
            borderwidth=0,
            font=("Courier New", 9),
        )
        self.terminal_listbox.place(relx=0, rely=0, relwidth=1, relheight=1, y=30)

        # Setup the listbox logger handler
        listbox_handler = ListboxHandler(self.terminal_listbox)
        listbox_handler.setLevel(Logger._logger_level)
        Logger.logger.addHandler(listbox_handler)

    def toggle_size(self):
        if not self.is_minimized:
            self.canvas.config(height=self.initial_height, width=self.initial_width)
            self.root.geometry(f"{self.initial_width}x{self.initial_height}+{self.screen_width//2 - self.initial_width//2}+0")
        else:
            self.canvas.config(height=self.maximized_height, width=self.initial_width)
            self.root.geometry(f"{self.initial_width}x{self.maximized_height}+{self.screen_width//2 - self.initial_width//2}+0")
        self.is_minimized = not self.is_minimized
        move_window_to_foreground()

    def filter_items(self):
        if self.loot_filter_thread is not None:
            Logger.info("Stoping Filter process")
            kill_thread(self.loot_filter_thread)
            self.loot_filter_thread = None
            return
        if self.is_minimized:
            self.toggle_size()
        self.loot_filter_thread = threading.Thread(target=self._wrapper_run_loot_filter, daemon=True)
        self.loot_filter_thread.start()

    def _wrapper_run_loot_filter(self):
        try:
            run_loot_filter()
        finally:
            self.loot_filter_thread = None

    def run(self):
        self.root.mainloop()