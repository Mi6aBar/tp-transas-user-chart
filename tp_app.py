# -*- coding: utf-8 -*-
"""
T&P CHART MASTER — portable GUI (маршрут + весь мир).
Transas / Furuno / JRC. Запуск: TP_Chart_Master.exe или python tp_app.py
"""
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
import webbrowser
from tkinter import filedialog, messagebox, ttk

APP_VERSION = '1.1'


def _setup_import_path():
    root = os.path.dirname(os.path.abspath(__file__))
    if getattr(sys, 'frozen', False):
        sys.path.insert(0, sys._MEIPASS)
    else:
        sys.path.insert(0, os.path.join(root, 'payload'))


_setup_import_path()

from adc_paths import (  # noqa: E402
    CHART_FORMATS,
    CHART_TRANSAS,
    OUTPUT_DIR_NAME,
    catalogue_candidates,
    default_output_dir,
    detect_defaults,
    exe_from_install_dir,
    find_adc_exe,
    find_catalogue,
    get_app_dir,
    load_config,
    normalize_chart_format,
    reveal_in_explorer,
    save_config,
    world_output_path,
)
from generate_from_export import generate_from_export  # noqa: E402
from generate_world_tpnm_aiz import build_world_chart  # noqa: E402
from extract_notice_list import extract_notice_list as build_notice_list  # noqa: E402
from route_watcher import RouteWatcher  # noqa: E402
from i18n import (  # noqa: E402
    LANG_EN,
    LANG_RU,
    chart_code_to_label,
    chart_format_labels,
    label_to_chart_code,
    label_to_lang_code,
    lang_code_to_label,
    language_option_labels,
    localize_error,
    resolve_language,
    t,
)


class TPTransasApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.lang = resolve_language()
        self._ui = {}
        self.minsize(520, 360)
        self._set_window_icon()
        self.defaults = detect_defaults()
        self._log_queue = queue.Queue()
        self._world_worker = None
        self._world_building = False
        self._status_key = None
        self._status_kwargs = {}
        self._watcher = RouteWatcher(
            on_log=lambda _msg: None,
            on_success=self._on_route_built,
        )
        self._build()
        self._load_settings()
        self._apply_language()
        self.after(200, self._auto_start_watcher)
        self.after(100, self._apply_windows_taskbar_icon)
        self.protocol('WM_DELETE_WINDOW', self._on_close)
        self.after(150, self._poll_log)

    def tr(self, key, **kwargs):
        return t(key, self.lang, **kwargs)

    def set_status(self, key=None, **kwargs):
        if key is None:
            self._status_key = None
            self._status_kwargs = {}
            self.status.set('')
            return
        self._status_key = key
        self._status_kwargs = dict(kwargs)
        self.status.set(self.tr(key, **kwargs))

    def show_error(self, message):
        messagebox.showerror(self.tr('window_title'), localize_error(str(message), self.lang))

    def _set_window_icon(self):
        bases = [get_app_dir()]
        if getattr(sys, 'frozen', False):
            bases.append(sys._MEIPASS)
        for base in bases:
            png_path = os.path.join(base, 'app_icon.png')
            if os.path.isfile(png_path):
                try:
                    img = tk.PhotoImage(file=png_path)
                    self.iconphoto(True, img)
                    self._icon_img = img
                    return
                except tk.TclError:
                    pass
            ico_path = os.path.join(base, 'TP_Transas.ico')
            if os.path.isfile(ico_path):
                try:
                    self.iconbitmap(ico_path)
                    return
                except tk.TclError:
                    continue

    def _apply_windows_taskbar_icon(self):
        if sys.platform != 'win32':
            return
        ico_path = None
        for base in ([get_app_dir()] + ([sys._MEIPASS] if getattr(sys, 'frozen', False) else [])):
            candidate = os.path.join(base, 'TP_Transas.ico')
            if os.path.isfile(candidate):
                ico_path = os.path.abspath(candidate)
                break
        if not ico_path:
            return
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            if not hwnd:
                hwnd = self.winfo_id()
            load = ctypes.windll.user32.LoadImageW
            send = ctypes.windll.user32.SendMessageW
            for size, icon_type in ((16, 0), (32, 0), (48, 1)):
                hicon = load(0, ico_path, 1, size, size, 0x0010)
                if hicon:
                    send(hwnd, 0x0080, icon_type, hicon)
        except Exception:
            pass

    def _build(self):
        pad = {'padx': 8, 'pady': 3}
        outer = ttk.Frame(self, padding=10)
        outer.grid(row=0, column=0, sticky='nsew')
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(1, weight=1)

        self._ui['hdr'] = ttk.Label(
            outer,
            text='',
            font=('Segoe UI', 11, 'bold'),
        )
        self._ui['hdr'].grid(row=0, column=0, sticky='w', pady=(0, 8))

        self._nb = ttk.Notebook(outer)
        self._nb.grid(row=1, column=0, sticky='nsew')

        self.tab_settings = ttk.Frame(self._nb, padding=8)
        self.tab_route = ttk.Frame(self._nb, padding=8)
        self.tab_world = ttk.Frame(self._nb, padding=8)
        self.tab_list = ttk.Frame(self._nb, padding=8)
        self._nb.add(self.tab_settings, text='')
        self._nb.add(self.tab_route, text='')
        self._nb.add(self.tab_world, text='')
        self._nb.add(self.tab_list, text='')

        self._build_settings(self.tab_settings, pad)
        self._build_route(self.tab_route, pad)
        self._build_world(self.tab_world, pad)
        self._build_list(self.tab_list, pad)

        self.status = tk.StringVar(value='')
        ttk.Label(outer, textvariable=self.status, wraplength=580).grid(
            row=2, column=0, sticky='w', pady=(6, 0))

        self._auth_frame = ttk.Frame(outer)
        self._auth_frame.grid(row=3, column=0, sticky='w', pady=(8, 0))
        self._ui['auth_by'] = ttk.Label(self._auth_frame, text='')
        self._ui['auth_by'].pack(side='left')
        self._ui['auth_dev'] = tk.Label(
            self._auth_frame, text='', fg='#0066cc', cursor='hand2')
        self._ui['auth_dev'].pack(side='left')
        self._ui['auth_dev'].bind(
            '<Button-1>', lambda _e: webbrowser.open('https://t.me/mishabar'))
        ttk.Label(self._auth_frame, text='  |  ').pack(side='left')
        self._ui['auth_channel'] = tk.Label(
            self._auth_frame, text='', fg='#0066cc', cursor='hand2')
        self._ui['auth_channel'].pack(side='left')
        self._ui['auth_channel'].bind(
            '<Button-1>', lambda _e: webbrowser.open('https://t.me/sea_apks'))

    def _build_settings(self, frm, pad):
        frm.columnconfigure(1, weight=1)

        self._ui['lbl_adc'] = ttk.Label(frm, text='')
        self._ui['lbl_adc'].grid(row=0, column=0, sticky='w')
        self.adc_dir = tk.StringVar()
        ttk.Entry(frm, textvariable=self.adc_dir).grid(row=0, column=1, sticky='ew', **pad)
        ttk.Button(frm, text='…', width=3, command=self.browse_adc).grid(row=0, column=2, **pad)

        self._ui['lbl_catalogue'] = ttk.Label(frm, text='')
        self._ui['lbl_catalogue'].grid(row=1, column=0, sticky='w')
        self.catalogue = tk.StringVar()
        ttk.Entry(frm, textvariable=self.catalogue).grid(row=1, column=1, sticky='ew', **pad)
        ttk.Button(frm, text='…', width=3, command=self.browse_catalogue).grid(row=1, column=2, **pad)

        self._ui['lbl_output'] = ttk.Label(frm, text='')
        self._ui['lbl_output'].grid(row=2, column=0, sticky='w')
        self.output_dir = tk.StringVar()
        ttk.Entry(frm, textvariable=self.output_dir).grid(row=2, column=1, sticky='ew', **pad)
        ttk.Button(frm, text='…', width=3, command=self.browse_output_dir).grid(row=2, column=2, **pad)

        self._ui['lbl_program_dir'] = ttk.Label(frm, text='')
        self._ui['lbl_program_dir'].grid(row=3, column=0, sticky='w')
        ttk.Label(frm, text=get_app_dir(), foreground='gray').grid(row=3, column=1, columnspan=2, sticky='w', **pad)

        self._ui['lbl_language'] = ttk.Label(frm, text='')
        self._ui['lbl_language'].grid(row=4, column=0, sticky='w')
        self.lang_var = tk.StringVar()
        self._lang_combo = ttk.Combobox(
            frm,
            textvariable=self.lang_var,
            values=list(language_option_labels(self.lang).values()),
            state='readonly',
            width=14,
        )
        self._lang_combo.grid(row=4, column=1, sticky='w', **pad)
        self._lang_combo.bind('<<ComboboxSelected>>', self._on_language_changed)

        self._ui['lbl_chart_format'] = ttk.Label(frm, text='')
        self._ui['lbl_chart_format'].grid(row=5, column=0, sticky='w')
        self.chart_format_var = tk.StringVar()
        self._format_combo = ttk.Combobox(
            frm,
            textvariable=self.chart_format_var,
            values=list(chart_format_labels(self.lang).values()),
            state='readonly',
            width=28,
        )
        self._format_combo.grid(row=5, column=1, sticky='w', **pad)

        save_row = ttk.Frame(frm)
        save_row.grid(row=6, column=0, columnspan=3, pady=(12, 0))
        self._ui['btn_save'] = ttk.Button(save_row, text='', command=self.save_settings)
        self._ui['btn_save'].pack()

        self._ui['settings_hint'] = ttk.Label(frm, text='', wraplength=520, justify='left')
        self._ui['settings_hint'].grid(row=7, column=0, columnspan=3, sticky='w', pady=(16, 0))

    def _build_route(self, frm, pad):
        frm.columnconfigure(0, weight=1)
        self._ui['route_info'] = ttk.Label(frm, text='', justify='left', wraplength=540)
        self._ui['route_info'].grid(row=0, column=0, sticky='w', pady=(0, 8))

        row1 = ttk.Frame(frm)
        row1.grid(row=1, column=0, sticky='ew', pady=4)
        self._ui['btn_launch_adc'] = ttk.Button(row1, text='', command=self.launch_adc)
        self._ui['btn_launch_adc'].pack(side='left')
        self._ui['btn_build_pdf'] = ttk.Button(row1, text='', command=self.build_route_manual)
        self._ui['btn_build_pdf'].pack(side='left', padx=8)
        self._ui['btn_open_output_route'] = ttk.Button(row1, text='', command=self.open_output_dir)
        self._ui['btn_open_output_route'].pack(side='right')

    def _build_world(self, frm, pad):
        frm.columnconfigure(0, weight=1)
        self._ui['world_info'] = ttk.Label(frm, text='', justify='left', wraplength=540)
        self._ui['world_info'].grid(row=0, column=0, sticky='w', pady=(0, 8))

        row_btn = ttk.Frame(frm)
        row_btn.grid(row=1, column=0, sticky='ew', pady=4)
        self.btn_world_build = ttk.Button(row_btn, text='', command=self.start_world_build)
        self.btn_world_build.pack(side='left')
        self._ui['btn_open_output_world'] = ttk.Button(row_btn, text='', command=self.open_output_dir)
        self._ui['btn_open_output_world'].pack(side='right')

    def _build_list(self, frm, pad):
        frm.columnconfigure(0, weight=1)
        self._ui['list_info'] = ttk.Label(frm, text='', justify='left', wraplength=540)
        self._ui['list_info'].grid(row=0, column=0, sticky='w', pady=(0, 8))

        row1 = ttk.Frame(frm)
        row1.grid(row=1, column=0, sticky='ew', pady=4)
        self._ui['btn_pick_file'] = ttk.Button(row1, text='', command=self.pick_notice_list_file)
        self._ui['btn_pick_file'].pack(side='left')
        self._ui['btn_open_output_list'] = ttk.Button(row1, text='', command=self.open_output_dir)
        self._ui['btn_open_output_list'].pack(side='right')

    def _apply_language(self):
        from i18n import DEFAULT_ADC_PATH, DEFAULT_CATALOGUE_PATH

        self.title('%s  v%s' % (self.tr('window_title'), APP_VERSION))
        self._ui['hdr'].configure(text=self.tr('header'))
        self._nb.tab(self.tab_settings, text=self.tr('tab_settings'))
        self._nb.tab(self.tab_route, text=self.tr('tab_route'))
        self._nb.tab(self.tab_world, text=self.tr('tab_world'))
        self._nb.tab(self.tab_list, text=self.tr('tab_list'))

        self._ui['lbl_adc'].configure(text=self.tr('lbl_adc_dir'))
        self._ui['lbl_catalogue'].configure(text=self.tr('lbl_catalogue'))
        self._ui['lbl_output'].configure(text=self.tr('lbl_output'))
        self._ui['lbl_program_dir'].configure(text=self.tr('lbl_program_dir'))
        self._ui['lbl_language'].configure(text=self.tr('lbl_language'))
        self._ui['lbl_chart_format'].configure(text=self.tr('lbl_chart_format'))
        self._ui['btn_save'].configure(text=self.tr('btn_save_settings'))
        self._ui['settings_hint'].configure(text=self.tr(
            'settings_hint',
            adc_path=DEFAULT_ADC_PATH,
            catalogue_path=DEFAULT_CATALOGUE_PATH,
        ))

        self._ui['route_info'].configure(text=self.tr('route_steps'))
        self._ui['btn_launch_adc'].configure(text=self.tr('btn_launch_adc'))
        self._ui['btn_build_pdf'].configure(text=self.tr('btn_build_pdf'))
        self._ui['btn_open_output_route'].configure(text=self.tr('btn_open_output'))

        self._ui['world_info'].configure(text=self.tr('world_info'))
        self.btn_world_build.configure(text=self.tr('btn_build_world'))
        self._ui['btn_open_output_world'].configure(text=self.tr('btn_open_output'))

        self._ui['list_info'].configure(text=self.tr('list_info'))
        self._ui['btn_pick_file'].configure(text=self.tr('btn_pick_file'))
        self._ui['btn_open_output_list'].configure(text=self.tr('btn_open_output'))

        fmt_labels = chart_format_labels(self.lang)
        self._format_combo.configure(values=list(fmt_labels.values()))
        cur_fmt = label_to_chart_code(self.chart_format_var.get(), self.lang)
        self.chart_format_var.set(chart_code_to_label(cur_fmt, self.lang))

        lang_opts = language_option_labels(self.lang)
        self._lang_combo.configure(values=list(lang_opts.values()))
        self.lang_var.set(lang_opts[self.lang])

        self._ui['auth_by'].configure(text=self.tr('auth_by') + ' ')
        self._ui['auth_dev'].configure(text=self.tr('auth_dev'))
        self._ui['auth_channel'].configure(text=self.tr('auth_channel'))

        if self._status_key:
            self.status.set(self.tr(self._status_key, **self._status_kwargs))

    def _on_language_changed(self, _event=None):
        prev_lang = self.lang
        self.lang = label_to_lang_code(self.lang_var.get(), prev_lang)
        self._apply_language()

    def _load_settings(self):
        cfg = load_config()
        d = self.defaults
        self.adc_dir.set(cfg.get('adc_install_dir') or d.get('adc_install_dir', ''))
        self.catalogue.set(cfg.get('catalogue_path') or d.get('catalogue_path', ''))
        self.output_dir.set(cfg.get('output_dir') or d.get('output_dir', ''))
        self.lang = resolve_language(cfg)
        self.lang_var.set(lang_code_to_label(self.lang, self.lang))
        fmt = normalize_chart_format(cfg.get('chart_format', CHART_TRANSAS))
        if fmt not in CHART_FORMATS:
            fmt = CHART_TRANSAS
        self.chart_format_var.set(chart_code_to_label(fmt, self.lang))

    def persist_settings(self):
        adc = self.adc_dir.get().strip()
        cat = self.catalogue.get().strip()
        out = self.output_dir.get().strip()
        if not out:
            out = os.path.join(get_app_dir(), OUTPUT_DIR_NAME)
        os.makedirs(out, exist_ok=True)
        self.lang = label_to_lang_code(self.lang_var.get(), self.lang)
        chart_fmt = label_to_chart_code(self.chart_format_var.get(), self.lang)
        cfg = load_config()
        cfg.pop('world_output_path', None)
        cfg.update({
            'adc_install_dir': adc,
            'adc_exe': exe_from_install_dir(adc) or cfg.get('adc_exe', ''),
            'catalogue_path': cat,
            'output_dir': os.path.abspath(out),
            'ui_language': self.lang,
            'chart_format': chart_fmt,
        })
        save_config(cfg)

    def save_settings(self):
        self.persist_settings()
        self._apply_language()
        self.set_status('msg_settings_saved')
        messagebox.showinfo(
            self.tr('window_title'),
            self.tr('msg_settings_saved_path', path=os.path.join(get_app_dir(), 'config.json')),
        )

    def _ensure_watcher_running(self):
        if self._watcher.running:
            return True
        cat = self.catalogue.get().strip() or find_catalogue()
        if not cat or not os.path.isfile(cat):
            return False
        self.persist_settings()
        self._watcher.start()
        return True

    def _auto_start_watcher(self):
        self._ensure_watcher_running()

    def browse_adc(self):
        path = filedialog.askdirectory(title=self.tr('dlg_adc_folder'))
        if not path:
            return
        self.adc_dir.set(path)
        common = os.path.join(os.environ.get('PROGRAMDATA', ''), 'ADMIRALTY_Digital_Catalogue')
        for cand in catalogue_candidates(path, common if os.path.isdir(common) else None):
            if os.path.isfile(cand):
                self.catalogue.set(os.path.abspath(cand))
                break

    def browse_catalogue(self):
        path = filedialog.askopenfilename(
            title=self.tr('dlg_catalogue'),
            filetypes=[(self.tr('filetype_catalogue'), '*.xml;*.zip'), (self.tr('filetype_all'), '*.*')],
        )
        if path:
            self.catalogue.set(path)

    def browse_output_dir(self):
        path = filedialog.askdirectory(title=self.tr('dlg_output_folder'))
        if path:
            self.output_dir.set(path)

    def _validate_catalogue(self, silent=False):
        self.persist_settings()
        cat = find_catalogue()
        if not cat or not os.path.isfile(cat):
            if not silent:
                messagebox.showerror(self.tr('window_title'), self.tr('err_catalogue_missing'))
            return None
        return cat

    def _poll_log(self):
        try:
            while True:
                item = self._log_queue.get_nowait()
                if item is None:
                    continue
                if isinstance(item, tuple):
                    kind, payload = item[0], item[1]
                    if kind == 'world_done':
                        self._on_world_success(payload)
                    elif kind == 'world_err':
                        self._on_world_error(payload)
        except queue.Empty:
            pass
        self.after(150, self._poll_log)

    def _world_build_done(self, result):
        self._world_building = False
        self._world_worker = None
        self._on_world_success(result)

    def _world_build_failed(self, err):
        self._world_building = False
        self._world_worker = None
        self._on_world_error(str(err))

    def launch_adc(self):
        self.persist_settings()
        adc = find_adc_exe()
        if not adc:
            messagebox.showerror(self.tr('window_title'), self.tr('err_adc_not_found'))
            return
        self._ensure_watcher_running()
        subprocess.Popen([adc])
        self.set_status('status_adc_started')

    def build_route_manual(self):
        cat = self._validate_catalogue()
        if not cat:
            return
        path = filedialog.askopenfilename(
            title=self.tr('dlg_route_pdf'),
            filetypes=[(self.tr('filetype_pdf'), '*.pdf')],
        )
        if not path:
            return
        self.set_status('status_build_route')
        try:
            result = generate_from_export(path)
            self._on_route_built(result)
        except Exception as exc:
            self.show_error(exc)

    def _show_furuno_result(self, result):
        files = result.get('furuno_files', 0)
        if not files:
            return
        folder = result.get('furuno_output_dir') or result.get('output', '')
        messagebox.showinfo(
            self.tr('window_title'),
            self.tr(
                'info_furuno_split',
                files=files,
                points=result.get('furuno_points', 0),
                folder=folder,
            ),
        )
        skipped = result.get('furuno_skipped', 0)
        if skipped:
            messagebox.showwarning(
                self.tr('window_title'),
                self.tr(
                    'warn_furuno_skipped',
                    skipped=skipped,
                    limit=result.get('furuno_limit', 200),
                ),
            )

    def _on_route_built(self, result):
        out = result.get('output')
        if result.get('furuno_files'):
            self.set_status(
                'status_furuno_ready',
                files=result.get('furuno_files', 1),
                count=result.get('objects', 0),
            )
            self._show_furuno_result(result)
        else:
            self.set_status('status_route_updated', count=result.get('objects', 0))
        if out and (os.path.isfile(out) or os.path.isdir(out)):
            reveal_in_explorer(out)
        elif out:
            reveal_in_explorer(os.path.dirname(os.path.abspath(out)))

    def open_output_dir(self):
        reveal_in_explorer(default_output_dir())

    def pick_notice_list_file(self):
        path = filedialog.askopenfilename(
            title=self.tr('dlg_notice_pdf'),
            filetypes=[(self.tr('filetype_pdf'), '*.pdf'), (self.tr('filetype_all'), '*.*')],
        )
        if not path:
            return
        self.persist_settings()
        self.set_status('status_extracting')
        try:
            result = build_notice_list(path, lang=self.lang)
        except Exception as exc:
            self.set_status()
            self.show_error(exc)
            return
        count = result.get('count', 0)
        out = result.get('output')
        if count == 0:
            self.set_status('warn_no_notices')
            messagebox.showwarning(self.tr('window_title'), self.tr('warn_no_notices_pattern'))
            return
        self.set_status('status_list_saved', count=count)
        if out and os.path.isfile(out):
            reveal_in_explorer(out)

    def start_world_build(self):
        if self._world_building or (self._world_worker and self._world_worker.is_alive()):
            return
        cat = self._validate_catalogue()
        if not cat:
            return
        self.persist_settings()
        out = world_output_path()

        self._world_building = True
        self.btn_world_build.configure(state='disabled')
        self.set_status('status_build_world')

        def worker():
            try:
                result = build_world_chart(cat, out)
                self.after(0, lambda r=result: self._world_build_done(r))
            except Exception as exc:
                self.after(0, lambda e=exc: self._world_build_failed(e))

        self._world_worker = threading.Thread(target=worker, daemon=True)
        self._world_worker.start()

    def _on_world_success(self, result):
        self.btn_world_build.configure(state='normal')
        if result.get('furuno_files'):
            self.set_status(
                'status_furuno_world',
                files=result.get('furuno_files', 1),
                count=result.get('objects', 0),
            )
            self._show_furuno_result(result)
        else:
            self.set_status('status_world_ready', count=result.get('objects', 0))
        out = result.get('output')
        if out and (os.path.isfile(out) or os.path.isdir(out)):
            reveal_in_explorer(out)
        elif out:
            reveal_in_explorer(os.path.dirname(os.path.abspath(out)))

    def _on_world_error(self, err):
        self.btn_world_build.configure(state='normal')
        self.set_status('status_build_error')
        self.show_error(err)

    def _on_close(self):
        if self._watcher.running:
            self._watcher.stop()
        self.destroy()


def main():
    os.makedirs(os.path.join(get_app_dir(), OUTPUT_DIR_NAME), exist_ok=True)
    os.makedirs(os.path.join(get_app_dir(), 'spool'), exist_ok=True)
    app = TPTransasApp()
    app.mainloop()


if __name__ == '__main__':
    main()
