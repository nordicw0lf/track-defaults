"""Track Defaults — a local Windows desktop application."""
from pathlib import Path
import os
import queue
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tracks import Video, KEEP, NONE, SUPPORTED, inspect, label, language, match_language, save, Cancelled


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Track Defaults')
        self.geometry('1180x760')
        self.minsize(960, 650)
        self.configure(bg='#f3f5f9')
        self.videos = {}
        self.events = queue.Queue()
        self.cancel = threading.Event()
        self.busy = False
        self.controls = []
        self.active = None
        self.output = tk.StringVar()
        self.status = tk.StringVar(value='Add videos to get started. Everything stays on your PC.')
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('.', font=('Segoe UI', 10), background='#f3f5f9', foreground='#172338')
        style.configure('TButton', padding=(12, 7))
        style.configure('Accent.TButton', background='#2563eb', foreground='white')
        style.map('Accent.TButton', background=[('active', '#1d4ed8'), ('disabled', '#a9b8d3')])
        style.configure('Treeview', rowheight=34, background='white', fieldbackground='white', borderwidth=0)
        style.configure('Treeview.Heading', font=('Segoe UI', 10, 'bold'), padding=8)
        style.map('Treeview', background=[('selected', '#dce8ff')], foreground=[('selected', '#142b50')])

        shell = ttk.Frame(self, padding=24)
        shell.pack(fill='both', expand=True)
        ttk.Label(shell, text='Track Defaults', font=('Segoe UI', 25, 'bold')).pack(anchor='w')
        ttk.Label(shell, text='Your videos. Your languages. Ready when you press play.', foreground='#63718a').pack(anchor='w', pady=(3, 18))
        toolbar = ttk.Frame(shell)
        toolbar.pack(fill='x', pady=(0, 12))
        self.button(toolbar, '＋ Add videos', self.add_files, accent=True).pack(side='left')
        self.button(toolbar, 'Add folder', self.add_folder).pack(side='left', padx=8)
        self.button(toolbar, 'Remove selected', self.remove).pack(side='left')
        ttk.Label(toolbar, text='MKV · MP4 · M4V · MOV', foreground='#63718a').pack(side='right')

        table = ttk.Frame(shell)
        table.pack(fill='both', expand=True)
        self.tree = ttk.Treeview(table, columns=('file', 'audio', 'subtitle', 'status'), show='headings', selectmode='extended', height=8)
        for key, title, width in [('file', 'VIDEO', 310), ('audio', 'DEFAULT AUDIO', 250), ('subtitle', 'DEFAULT SUBTITLE', 250), ('status', 'STATUS', 140)]:
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, minwidth=90)
        self.tree.pack(side='left', fill='both', expand=True)
        scrollbar = ttk.Scrollbar(table, orient='vertical', command=self.tree.yview)
        scrollbar.pack(side='right', fill='y')
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.bind('<<TreeviewSelect>>', self.select)

        editor = ttk.LabelFrame(shell, text='  Selected video  ', padding=12)
        editor.pack(fill='x', pady=(14, 10))
        self.file_label = ttk.Label(editor, text='Select a video to inspect its tracks.', foreground='#63718a')
        self.file_label.pack(anchor='w', pady=(0, 7))
        row = ttk.Frame(editor)
        row.pack(fill='x')
        ttk.Label(row, text='Audio').pack(side='left', padx=(0, 8))
        self.audio = ttk.Combobox(row, state='disabled', width=47)
        self.audio.pack(side='left', fill='x', expand=True)
        ttk.Label(row, text='Subtitles').pack(side='left', padx=(18, 8))
        self.subtitle = ttk.Combobox(row, state='disabled', width=47)
        self.subtitle.pack(side='left', fill='x', expand=True)
        self.audio.bind('<<ComboboxSelected>>', lambda e: self.change('audio'))
        self.subtitle.bind('<<ComboboxSelected>>', lambda e: self.change('subtitle'))

        batch = ttk.LabelFrame(shell, text='  Batch language choices  ', padding=12)
        batch.pack(fill='x')
        row = ttk.Frame(batch)
        row.pack(fill='x')
        ttk.Label(row, text='Audio').pack(side='left', padx=(0, 8))
        self.batch_audio = ttk.Combobox(row, state='readonly', width=19, values=[KEEP])
        self.batch_audio.set(KEEP)
        self.batch_audio.pack(side='left')
        ttk.Label(row, text='Subtitles').pack(side='left', padx=(18, 8))
        self.batch_subtitle = ttk.Combobox(row, state='readonly', width=22, values=[KEEP, NONE])
        self.batch_subtitle.set(KEEP)
        self.batch_subtitle.pack(side='left')
        self.button(row, 'Apply to selected', lambda: self.apply_batch(False)).pack(side='left', padx=(18, 8))
        self.button(row, 'Apply to all', lambda: self.apply_batch(True)).pack(side='left')
        ttk.Label(batch, text='Matches by language, even if track order differs. Missing or ambiguous matches are left for you to choose.', foreground='#63718a').pack(anchor='w', pady=(8, 0))

        destination = ttk.Frame(shell)
        destination.pack(fill='x', pady=(14, 8))
        ttk.Label(destination, text='Save copies to').pack(side='left', padx=(0, 10))
        self.out_entry = ttk.Entry(destination, textvariable=self.output)
        self.out_entry.pack(side='left', fill='x', expand=True)
        self.button(destination, 'Browse…', self.browse).pack(side='left', padx=(8, 0))
        footer = ttk.Frame(shell)
        footer.pack(fill='x')
        self.button(footer, 'Save all planned changes', self.start_save, accent=True).pack(side='right')
        self.cancel_button = ttk.Button(footer, text='Cancel', command=self.cancel.set, state='disabled')
        self.cancel_button.pack(side='right', padx=8)
        ttk.Label(footer, text='Originals kept • No re-encoding', foreground='#63718a').pack(side='left')
        self.progress = ttk.Progressbar(shell, mode='indeterminate')
        self.progress.pack(fill='x', pady=(12, 6))
        ttk.Label(shell, textvariable=self.status, wraplength=1080).pack(anchor='w')
        self.after(100, self.drain)
        self.protocol('WM_DELETE_WINDOW', self.close)

    def button(self, parent, text, action, accent=False):
        button = ttk.Button(parent, text=text, command=action, style='Accent.TButton' if accent else 'TButton')
        self.controls.append(button)
        return button

    def set_busy(self, busy):
        self.busy = busy
        for button in self.controls:
            button.configure(state='disabled' if busy else 'normal')
        for combo in [self.batch_audio, self.batch_subtitle]:
            combo.configure(state='disabled' if busy else 'readonly')
        self.out_entry.configure(state='disabled' if busy else 'normal')
        self.cancel_button.configure(state='normal' if busy else 'disabled')
        if busy:
            self.cancel.clear()
            self.progress.start(12)
        else:
            self.progress.stop()
        self.select()

    def add_files(self):
        paths = filedialog.askopenfilenames(title='Choose videos', filetypes=[('Videos', '*.mkv *.mp4 *.m4v *.mov')])
        self.scan(paths)

    def add_folder(self):
        directory = filedialog.askdirectory(title='Choose a folder of videos')
        if directory:
            self.scan(sorted(p for p in Path(directory).iterdir() if p.suffix.lower() in SUPPORTED))

    def scan(self, paths):
        existing = {str(v.path).casefold() for v in self.videos.values()}
        paths = list(dict.fromkeys(Path(p).resolve() for p in paths))
        paths = [p for p in paths if str(p).casefold() not in existing]
        if not paths:
            return
        if not self.output.get():
            self.output.set(str(paths[0].parent / 'Track Defaults'))
        self.set_busy(True)
        def work():
            errors = []
            for i, path in enumerate(paths):
                if self.cancel.is_set():
                    break
                self.events.put(('status', f'Reading {i + 1}/{len(paths)}: {path.name}'))
                try:
                    self.events.put(('video', Video(path, inspect(path))))
                except Exception as exc:
                    errors.append(f'{path.name}: {exc}')
            self.events.put(('scan_done', errors))
        threading.Thread(target=work, daemon=True).start()

    def refresh(self, key):
        v = self.videos[key]
        self.tree.item(key, values=(v.path.name, v.describe('audio'), v.describe('subtitle'), v.status))

    def select(self, event=None):
        selected = self.tree.selection()
        self.active = selected[0] if selected else None
        for kind, combo in [('audio', self.audio), ('subtitle', self.subtitle)]:
            combo.configure(state='disabled')
            combo.set('')
            if self.active:
                v = self.videos[self.active]
                streams = v.streams(kind)
                choices = [KEEP] + ([NONE] if kind == 'subtitle' else [])
                values = choices + [label(s, i) for i, s in enumerate(streams)]
                combo.configure(values=values, state='disabled' if self.busy else 'readonly')
                choice = getattr(v, kind)
                combo.current(choices.index(choice) if isinstance(choice, str) else len(choices) + [s['index'] for s in streams].index(choice))
        self.file_label.configure(text=(self.videos[self.active].path.name + (f'  •  {len(selected)} selected; editing first video' if len(selected) > 1 else '')) if self.active else 'Select a video to inspect its tracks.')

    def change(self, kind):
        if self.busy or not self.active:
            return
        combo = self.audio if kind == 'audio' else self.subtitle
        v = self.videos[self.active]
        choices = [KEEP] + ([NONE] if kind == 'subtitle' else [])
        choices += [s['index'] for s in v.streams(kind)]
        setattr(v, kind, choices[combo.current()])
        v.review.discard(kind)
        v.status = 'Needs review' if v.review else 'Planned'
        self.refresh(self.active)

    def apply_batch(self, all_files):
        keys = list(self.videos) if all_files else list(self.tree.selection())
        unresolved = []
        for key in keys:
            v = self.videos[key]
            issues = []
            v.review.clear()
            for kind, combo in [('audio', self.batch_audio), ('subtitle', self.batch_subtitle)]:
                wanted = combo.get()
                try:
                    choice = wanted if wanted in (KEEP, NONE) else match_language(v, kind, wanted)
                    setattr(v, kind, choice)
                except ValueError as exc:
                    # Remove any stale plan for the unresolved category.
                    setattr(v, kind, KEEP)
                    v.review.add(kind)
                    issues.append(f'{kind}: {exc}')
            v.status = 'Needs review' if issues else 'Planned'
            if issues:
                unresolved.append(v.path.name + ': ' + '; '.join(issues))
            self.refresh(key)
        self.select()
        self.status.set(f'Applied choices to {len(keys)} videos. {len(unresolved)} need review.')
        if unresolved:
            self.show_report('Choose tracks manually', '\n\n'.join(unresolved))

    def remove(self):
        for key in self.tree.selection():
            self.tree.delete(key)
            del self.videos[key]
        self.select()

    def browse(self):
        directory = filedialog.askdirectory(title='Save new copies here')
        if directory:
            self.output.set(directory)

    def start_save(self):
        pending = [(k, v) for k, v in self.videos.items() if v.status not in ('Saved', 'Needs review') and (v.audio != KEEP or v.subtitle != KEEP)]
        if not pending:
            messagebox.showinfo('Choose defaults first', 'Choose an audio or subtitle default for at least one video. Files marked Needs review require manual choices.')
            return
        if not self.output.get().strip():
            self.browse()
            if not self.output.get().strip():
                return
        directory = Path(self.output.get()).expanduser().resolve()
        self.set_busy(True)
        def work():
            saved, errors = [], []
            for i, (key, video) in enumerate(pending):
                if self.cancel.is_set():
                    break
                self.events.put(('status', f'Saving {i + 1}/{len(pending)}: {video.path.name}'))
                self.events.put(('state', (key, 'Saving…', '')))
                try:
                    result = save(video, directory, self.cancel)
                    saved.append(str(result))
                    self.events.put(('state', (key, 'Saved', str(result))))
                except Cancelled:
                    self.events.put(('state', (key, 'Cancelled', '')))
                    break
                except Exception as exc:
                    errors.append(f'{video.path.name}: {exc}')
                    self.events.put(('state', (key, 'Failed', '')))
            self.events.put(('save_done', (saved, errors, self.cancel.is_set())))
        threading.Thread(target=work, daemon=True).start()

    def drain(self):
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == 'status':
                    self.status.set(payload)
                elif kind == 'video':
                    key = self.tree.insert('', 'end')
                    self.videos[key] = payload
                    self.refresh(key)
                elif kind == 'state':
                    key, status, output = payload
                    self.videos[key].status, self.videos[key].output = status, output
                    self.refresh(key)
                elif kind == 'scan_done':
                    self.set_busy(False)
                    for stream_kind, combo in [('audio', self.batch_audio), ('subtitle', self.batch_subtitle)]:
                        languages = sorted({language(s) for v in self.videos.values() for s in v.streams(stream_kind)})
                        combo.configure(values=[KEEP] + ([NONE] if stream_kind == 'subtitle' else []) + languages)
                    self.status.set(f'{len(self.videos)} videos ready. Select a row to choose tracks, or apply batch language choices.')
                    if self.videos and not self.tree.selection():
                        self.tree.selection_set(next(iter(self.videos)))
                    if payload:
                        self.show_report('Could not read some videos', '\n\n'.join(payload))
                elif kind == 'save_done':
                    saved, errors, cancelled = payload
                    self.set_busy(False)
                    summary = f'{"Cancelled. " if cancelled else "Finished. "}{len(saved)} copies saved; {len(errors)} failed. Originals are unchanged.'
                    self.status.set(summary)
                    self.show_report('Batch results', summary + '\n\n' + '\n'.join(saved) + ('\n\nErrors:\n' + '\n\n'.join(errors) if errors else ''))
        except queue.Empty:
            pass
        self.after(100, self.drain)

    def show_report(self, title, content):
        window = tk.Toplevel(self)
        window.title(title)
        window.geometry('760x400')
        text = tk.Text(window, wrap='word', font=('Segoe UI', 10), padx=16, pady=16)
        text.pack(fill='both', expand=True)
        text.insert('1.0', content)
        text.configure(state='disabled')
        ttk.Button(window, text='Close', command=window.destroy).pack(pady=10)

    def close(self):
        if self.busy:
            self.cancel.set()
            self.status.set('Cancelling safely. You can close the app when the current operation stops.')
        else:
            self.destroy()

if __name__ == '__main__':
    import sys
    if len(sys.argv) == 3 and sys.argv[1] == '--self-test':
        from package_check import check
        raise SystemExit(check(sys.argv[2]))
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        pass
    App().mainloop()
