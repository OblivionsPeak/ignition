"""Ignition — launch your whole sim racing stack with one button.

One window: a checklist of apps, a GO button, a log. First run scans for what
you have installed and ticks it. Everything after that is drag-to-reorder and
an Edit dialog.

  GO         launches every ticked app, in order, waiting the per-app delay
             between them, skipping anything already running
  SHUTDOWN   closes them again in reverse order, politely first

Nothing here is iRacing-specific — it launches whatever you point it at.

CLI (all optional):
  --rescan    ignore the saved list and re-detect from scratch on startup
"""
import json
import queue
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import detect
from catalog import CATALOG

APP_NAME = 'Ignition'

def app_dir():
    return Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent

CONFIG_PATH = app_dir() / 'ignition.json'

# ---------------------------------------------------------------- theme

BG = '#15171c'
PANEL = '#1d2027'
LINE = '#2c313b'
TEXT = '#e8eaee'
MUTED = '#8b93a3'
GO = '#1c9e50'
GO_HOT = '#23b85e'
STOP = '#8a2f2a'
WARN = '#c9a227'

FIELDS = ('name', 'path', 'args', 'workdir', 'process', 'delay', 'admin',
          'skip_if_running', 'enabled')

def blank_app():
    return {'name': '', 'path': '', 'args': '', 'workdir': '', 'process': '',
            'delay': 2, 'admin': False, 'skip_if_running': True, 'enabled': True}

def load_config():
    try:
        data = json.loads(CONFIG_PATH.read_text('utf-8'))
        apps = []
        for a in data.get('apps', []):
            row = blank_app()
            row.update({k: v for k, v in a.items() if k in FIELDS})
            apps.append(row)
        return apps
    except Exception:
        return None

def save_config(apps):
    try:
        CONFIG_PATH.write_text(json.dumps({'apps': apps}, indent=2), 'utf-8')
    except Exception:
        pass

# ---------------------------------------------------------------- edit dialog

class EditDialog(tk.Toplevel):
    """Every field of one app. Kept deliberately plain — this is the screen
    nobody should have to open, so it just needs to be obvious when they do."""

    def __init__(self, parent, app, title='Edit app'):
        super().__init__(parent)
        self.result = None
        self.app = dict(app)
        self.title(title)
        self.configure(bg=PANEL)
        self.resizable(False, False)
        self.transient(parent)

        self.vars = {
            'name': tk.StringVar(value=app['name']),
            'path': tk.StringVar(value=app['path']),
            'args': tk.StringVar(value=app['args']),
            'workdir': tk.StringVar(value=app['workdir']),
            'process': tk.StringVar(value=app['process']),
            'delay': tk.StringVar(value=str(app['delay'])),
            'admin': tk.BooleanVar(value=app['admin']),
            'skip_if_running': tk.BooleanVar(value=app['skip_if_running']),
        }

        pad = {'padx': 12, 'pady': 5}
        row = 0
        for key, label, hint in (
            ('name', 'Name', ''),
            ('path', 'Program', 'the .exe or shortcut to launch'),
            ('args', 'Arguments', 'optional command line'),
            ('workdir', 'Start in', 'leave blank to use the program folder'),
            ('process', 'Process name(s)', 'comma-separated; used to skip if running, and to shut down'),
            ('delay', 'Wait after (s)', 'pause before launching the next app'),
        ):
            tk.Label(self, text=label, bg=PANEL, fg=TEXT, anchor='w',
                     font=('Segoe UI', 9)).grid(row=row, column=0, sticky='w', **pad)
            entry = tk.Entry(self, textvariable=self.vars[key], width=52,
                             bg=BG, fg=TEXT, insertbackground=TEXT,
                             relief='flat', font=('Segoe UI', 10))
            entry.grid(row=row, column=1, sticky='we', **pad)
            if key == 'path':
                tk.Button(self, text='Browse…', command=self._browse, bg=LINE, fg=TEXT,
                          relief='flat', font=('Segoe UI', 9)).grid(row=row, column=2, padx=(0, 12))
            if hint:
                row += 1
                tk.Label(self, text=hint, bg=PANEL, fg=MUTED, anchor='w',
                         font=('Segoe UI', 8)).grid(row=row, column=1, sticky='w', padx=12)
            row += 1

        tk.Checkbutton(self, text='Run as administrator', variable=self.vars['admin'],
                       bg=PANEL, fg=TEXT, selectcolor=BG, activebackground=PANEL,
                       activeforeground=TEXT, font=('Segoe UI', 9)
                       ).grid(row=row, column=1, sticky='w', padx=8)
        row += 1
        tk.Checkbutton(self, text="Skip if it's already running",
                       variable=self.vars['skip_if_running'],
                       bg=PANEL, fg=TEXT, selectcolor=BG, activebackground=PANEL,
                       activeforeground=TEXT, font=('Segoe UI', 9)
                       ).grid(row=row, column=1, sticky='w', padx=8)
        row += 1

        bar = tk.Frame(self, bg=PANEL)
        bar.grid(row=row, column=0, columnspan=3, sticky='e', padx=12, pady=12)
        tk.Button(bar, text='Cancel', command=self.destroy, bg=LINE, fg=TEXT,
                  relief='flat', width=10, font=('Segoe UI', 9)).pack(side='left', padx=4)
        tk.Button(bar, text='Save', command=self._save, bg=GO, fg='#ffffff',
                  relief='flat', width=10, font=('Segoe UI', 9, 'bold')).pack(side='left')

        self.grab_set()
        self.wait_window(self)

    def _browse(self):
        p = filedialog.askopenfilename(
            title='Choose a program or shortcut',
            filetypes=[('Programs and shortcuts', '*.exe;*.lnk;*.bat;*.cmd'),
                       ('All files', '*.*')])
        if not p:
            return
        info = detect.resolve_one(p)
        target = info.get('Target') or p
        self.vars['path'].set(target)
        if info.get('Args') and not self.vars['args'].get():
            self.vars['args'].set(info['Args'])
        if info.get('Work'):
            self.vars['workdir'].set(info['Work'])
        if not self.vars['process'].get():
            self.vars['process'].set(Path(target).name)
        if not self.vars['name'].get():
            self.vars['name'].set(Path(target).stem)

    def _save(self):
        out = dict(self.app)
        for k, v in self.vars.items():
            out[k] = v.get()
        if not out['name'].strip() or not out['path'].strip():
            messagebox.showwarning(APP_NAME, 'A name and a program are required.', parent=self)
            return
        try:
            out['delay'] = max(0, int(float(out['delay'])))
        except ValueError:
            out['delay'] = 2
        if not out['process'].strip():
            out['process'] = Path(out['path']).name
        self.result = out
        self.destroy()

# ---------------------------------------------------------------- main window

class Ignition:
    def __init__(self, force_rescan=False):
        self.apps = None if force_rescan else load_config()
        self.busy = False
        self.events = queue.Queue()

        self.root = tk.Tk()
        self.root.title(APP_NAME)
        self.root.configure(bg=BG)
        self.root.geometry('820x620')
        self.root.minsize(720, 540)

        self._build()
        self.root.after(80, self._pump)

        if self.apps is None:
            self.apps = []
            self._log('First run — looking for the apps you have installed.')
            self._scan_async()
        else:
            self._refresh_rows()
            self._refresh_status_async()

    # -- layout ----------------------------------------------------------

    def _build(self):
        head = tk.Frame(self.root, bg=BG)
        head.pack(fill='x', padx=18, pady=(16, 6))
        tk.Label(head, text='IGNITION', bg=BG, fg=TEXT,
                 font=('Segoe UI', 20, 'bold')).pack(side='left')
        tk.Label(head, text='  everything you need, before you drive',
                 bg=BG, fg=MUTED, font=('Segoe UI', 10)).pack(side='left', pady=(9, 0))

        style = ttk.Style()
        try:
            style.theme_use('clam')
        except tk.TclError:
            pass
        style.configure('I.Treeview', background=PANEL, fieldbackground=PANEL,
                        foreground=TEXT, rowheight=30, borderwidth=0,
                        font=('Segoe UI', 10))
        style.configure('I.Treeview.Heading', background=BG, foreground=MUTED,
                        relief='flat', font=('Segoe UI', 9))
        style.map('I.Treeview', background=[('selected', LINE)],
                  foreground=[('selected', TEXT)])

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill='both', expand=True, padx=18)

        cols = ('on', 'name', 'status', 'delay')
        self.tree = ttk.Treeview(body, columns=cols, show='headings',
                                 style='I.Treeview', selectmode='browse')
        self.tree.heading('on', text='')
        self.tree.heading('name', text='APP')
        self.tree.heading('status', text='STATUS')
        self.tree.heading('delay', text='WAIT')
        self.tree.column('on', width=38, anchor='center', stretch=False)
        self.tree.column('name', width=420, anchor='w')
        self.tree.column('status', width=200, anchor='w')
        self.tree.column('delay', width=70, anchor='center', stretch=False)
        self.tree.tag_configure('off', foreground=MUTED)
        self.tree.tag_configure('missing', foreground='#c96a62')
        self.tree.pack(side='left', fill='both', expand=True)

        bar = tk.Scrollbar(body, command=self.tree.yview, bg=BG,
                           troughcolor=BG, relief='flat', bd=0)
        bar.pack(side='right', fill='y')
        self.tree.configure(yscrollcommand=bar.set)

        self.tree.bind('<Button-1>', self._on_click)
        self.tree.bind('<B1-Motion>', self._on_drag)
        self.tree.bind('<Double-1>', self._on_double)

        tools = tk.Frame(self.root, bg=BG)
        tools.pack(fill='x', padx=18, pady=(8, 4))
        for label, cmd in (('Add…', self._add), ('Edit…', self._edit),
                           ('Remove', self._remove), ('Move up', lambda: self._move(-1)),
                           ('Move down', lambda: self._move(1)),
                           ('Rescan', self._scan_async)):
            tk.Button(tools, text=label, command=cmd, bg=PANEL, fg=TEXT, relief='flat',
                      font=('Segoe UI', 9), padx=12, pady=5).pack(side='left', padx=(0, 6))
        tk.Label(tools, text='drag a row to reorder', bg=BG, fg=MUTED,
                 font=('Segoe UI', 8)).pack(side='left', padx=8)

        actions = tk.Frame(self.root, bg=BG)
        actions.pack(fill='x', padx=18, pady=(6, 8))
        self.go_btn = tk.Button(actions, text='GO', command=self._go, bg=GO, fg='#ffffff',
                                relief='flat', font=('Segoe UI', 15, 'bold'),
                                padx=48, pady=10, activebackground=GO_HOT,
                                activeforeground='#ffffff')
        self.go_btn.pack(side='left')
        self.stop_btn = tk.Button(actions, text='SHUTDOWN', command=self._shutdown,
                                  bg=PANEL, fg=TEXT, relief='flat',
                                  font=('Segoe UI', 10), padx=20, pady=10)
        self.stop_btn.pack(side='left', padx=10)
        self.status = tk.Label(actions, text='', bg=BG, fg=MUTED, font=('Segoe UI', 9))
        self.status.pack(side='left', padx=10)

        self.log = tk.Text(self.root, height=8, bg=PANEL, fg=MUTED, relief='flat',
                           font=('Consolas', 9), wrap='word', padx=10, pady=8)
        self.log.pack(fill='both', padx=18, pady=(0, 16))
        self.log.configure(state='disabled')

    # -- rows ------------------------------------------------------------

    def _refresh_rows(self, statuses=None):
        pos = self.tree.yview()
        self.tree.delete(*self.tree.get_children())
        for i, a in enumerate(self.apps):
            st = (statuses or {}).get(i, '')
            tags = ()
            if not Path(detect.expand(a['path'])).exists():
                st, tags = 'not found', ('missing',)
            elif not a['enabled']:
                tags = ('off',)
            self.tree.insert('', 'end', iid=str(i),
                             values=('☑' if a['enabled'] else '☐', a['name'], st,
                                     f'{a["delay"]}s'), tags=tags)
        self.tree.yview_moveto(pos[0])

    def _selected(self):
        sel = self.tree.selection()
        return int(sel[0]) if sel else None

    def _on_click(self, event):
        row = self.tree.identify_row(event.y)
        if not row:
            return
        if self.tree.identify_column(event.x) == '#1':
            i = int(row)
            self.apps[i]['enabled'] = not self.apps[i]['enabled']
            save_config(self.apps)
            self._refresh_rows()
            self.tree.selection_set(str(i))
            return 'break'
        self._drag_from = int(row)

    def _on_drag(self, event):
        """Reorder by dragging. Moving in the tree and in the list together
        keeps iid == index, which everything else relies on."""
        if self.busy:
            return
        row = self.tree.identify_row(event.y)
        if not row:
            return
        src = getattr(self, '_drag_from', None)
        dst = int(row)
        if src is None or src == dst:
            return
        self.apps.insert(dst, self.apps.pop(src))
        self._drag_from = dst
        self._refresh_rows()
        self.tree.selection_set(str(dst))
        save_config(self.apps)

    def _on_double(self, event):
        if self.tree.identify_column(event.x) != '#1':
            self._edit()

    def _add(self):
        dlg = EditDialog(self.root, blank_app(), 'Add app')
        if dlg.result:
            self.apps.append(dlg.result)
            save_config(self.apps)
            self._refresh_rows()
            self._refresh_status_async()

    def _edit(self):
        i = self._selected()
        if i is None:
            return
        dlg = EditDialog(self.root, self.apps[i])
        if dlg.result:
            self.apps[i] = dlg.result
            save_config(self.apps)
            self._refresh_rows()
            self._refresh_status_async()

    def _remove(self):
        i = self._selected()
        if i is None:
            return
        if messagebox.askyesno(APP_NAME, f'Remove {self.apps[i]["name"]} from the list?'):
            self.apps.pop(i)
            save_config(self.apps)
            self._refresh_rows()

    def _move(self, step):
        i = self._selected()
        if i is None:
            return
        j = i + step
        if 0 <= j < len(self.apps):
            self.apps[i], self.apps[j] = self.apps[j], self.apps[i]
            save_config(self.apps)
            self._refresh_rows()
            self.tree.selection_set(str(j))

    # -- background work -------------------------------------------------

    def _log(self, msg):
        self.log.configure(state='normal')
        self.log.insert('end', msg + '\n')
        self.log.see('end')
        self.log.configure(state='disabled')

    def _emit(self, kind, payload=None):
        self.events.put((kind, payload))

    def _pump(self):
        while not self.events.empty():
            try:
                kind, payload = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == 'log':
                self._log(payload)
            elif kind == 'status':
                self.status.configure(text=payload)
            elif kind == 'rows':
                self._refresh_rows(payload)
            elif kind == 'apps':
                self.apps = payload
                save_config(self.apps)
                self._refresh_rows()
            elif kind == 'busy':
                self.busy = payload
                state = 'disabled' if payload else 'normal'
                self.go_btn.configure(state=state, bg=LINE if payload else GO)
                self.stop_btn.configure(state=state)
        self.root.after(80, self._pump)

    def _thread(self, fn):
        if self.busy:
            return
        self._emit('busy', True)

        def wrap():
            try:
                fn()
            except Exception as e:
                self._emit('log', f'! {e}')
            finally:
                self._emit('busy', False)
                self._emit('status', '')
        threading.Thread(target=wrap, daemon=True).start()

    def _scan_async(self):
        def work():
            self._emit('status', 'Scanning…')
            found = detect.detect_all(CATALOG, lambda m: self._emit('status', m))
            if not found:
                self._emit('log', 'Found nothing automatically — use Add… to '
                                  'point at your apps.')
                return
            known = {a['path'].lower() for a in (self.apps or [])}
            merged = list(self.apps or [])
            added = 0
            for row in found:
                if row['path'].lower() not in known:
                    merged.append(row)
                    added += 1
            self._emit('apps', merged)
            self._emit('log', f'Found {len(found)} app(s), added {added} new.')
        self._thread(work)

    def _refresh_status_async(self):
        def work():
            snap = detect.running_processes()
            statuses = {}
            for i, a in enumerate(self.apps):
                if detect.is_running(a['process'], snap):
                    statuses[i] = 'running'
                elif Path(detect.expand(a['path'])).exists():
                    statuses[i] = 'ready'
            self._emit('rows', statuses)
        self._thread(work)

    def _go(self):
        todo = [a for a in self.apps if a['enabled']]
        if not todo:
            self._log('Nothing ticked.')
            return

        def work():
            snap = detect.running_processes()
            started = skipped = failed = 0
            for n, a in enumerate(todo):
                self._emit('status', f'{n + 1}/{len(todo)}  {a["name"]}')
                if a['skip_if_running'] and detect.is_running(a['process'], snap):
                    self._emit('log', f'–  {a["name"]} already running')
                    skipped += 1
                    continue
                ok, err = detect.launch(a['path'], a['args'], a['workdir'], a['admin'])
                if ok:
                    self._emit('log', f'▸  {a["name"]}'
                                      + ('  (as administrator)' if a['admin'] else ''))
                    started += 1
                    for p in detect.process_list(a['process']):
                        snap.add(p.lower())
                else:
                    self._emit('log', f'!  {a["name"]} — {err}')
                    failed += 1
                if a['delay'] and n < len(todo) - 1:
                    time.sleep(a['delay'])
            self._emit('log', f'Done — {started} started, {skipped} already up, '
                              f'{failed} failed.')
            self._emit('rows', None)
            snap = detect.running_processes()
            self._emit('rows', {i: 'running' for i, a in enumerate(self.apps)
                                if detect.is_running(a['process'], snap)})
        self._thread(work)

    def _shutdown(self):
        targets = [a for a in self.apps if a['enabled'] and a['process']]
        if not targets:
            return
        names = '\n'.join(f'  {a["name"]}' for a in targets)
        if not messagebox.askyesno(APP_NAME, f'Close these?\n\n{names}'):
            return

        def work():
            # reverse order: the sim goes down before the things watching it
            for a in reversed(targets):
                self._emit('status', f'Closing {a["name"]}…')
                if not detect.is_running(a['process']):
                    continue
                if detect.stop(a['process']):
                    self._emit('log', f'×  {a["name"]} closed')
                else:
                    self._emit('log', f'!  {a["name"]} would not close')
            snap = detect.running_processes()
            self._emit('rows', {i: 'running' for i, a in enumerate(self.apps)
                                if detect.is_running(a['process'], snap)})
        self._thread(work)

    def run(self):
        self.root.mainloop()


def main():
    Ignition(force_rescan='--rescan' in sys.argv).run()


if __name__ == '__main__':
    main()
