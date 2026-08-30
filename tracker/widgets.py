"""小さな共通ウィジェット。"""

import tkinter as tk
from datetime import datetime
from tkinter import ttk


class LogView(ttk.LabelFrame):
    """時刻つきの追記専用ログ。"""

    def __init__(self, master, text='ログ', height=7):
        super().__init__(master, text=text)
        self.columnconfigure(0, weight=1)
        self._text = tk.Text(self, height=height, wrap='none')
        self._text.grid(row=0, column=0, sticky='ew')
        scroll = ttk.Scrollbar(self, orient='vertical', command=self._text.yview)
        scroll.grid(row=0, column=1, sticky='ns')
        self._text.configure(yscrollcommand=scroll.set, state='disabled')

    def append(self, message):
        self._text.configure(state='normal')
        self._text.insert('end', f'[{datetime.now().strftime("%H:%M:%S")}] {message}\n')
        self._text.see('end')
        self._text.configure(state='disabled')
