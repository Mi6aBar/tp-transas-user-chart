# -*- coding: utf-8 -*-
"""Фоновый watcher: PDF из ADC Print -> Route_T&P.aiz (встраивается в GUI)."""
import json
import os
import threading
import time
from datetime import datetime

from adc_paths import default_output_dir, find_catalogue, get_app_dir, route_aiz_path

WATCH_EXTENSIONS = {'.pdf'}
DEBOUNCE_SEC = 2.0
IGNORE_NAMES = {'watcher.log', 'watcher_state.json', 'watcher.pid', 'config.json'}


def _paths():
    base = get_app_dir()
    out_aiz = route_aiz_path()
    return {
        'base': base,
        'spool': os.path.join(base, 'spool'),
        'output_aiz': out_aiz,
        'state': os.path.join(base, 'watcher_state.json'),
        'log': os.path.join(base, 'watcher.log'),
    }


def log(msg, on_log=None):
    paths = _paths()
    line = '[%s] %s' % (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), msg)
    try:
        with open(paths['log'], 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except OSError:
        pass
    if on_log:
        on_log(line)


def load_state():
    path = _paths()['state']
    if os.path.isfile(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (OSError, ValueError):
            pass
    return {'processed': {}}


def save_state(state):
    with open(_paths()['state'], 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2)


def file_signature(path):
    try:
        st = os.stat(path)
        return '%d:%d' % (st.st_size, int(st.st_mtime))
    except OSError:
        return None


def watch_directories():
    home = os.path.expanduser('~')
    paths = _paths()
    dirs = [
        paths['spool'],
        paths['base'],
        default_output_dir(),
        os.path.join(home, 'Desktop'),
        os.path.join(home, 'Documents'),
        os.path.join(home, 'Downloads'),
    ]
    seen = set()
    out = []
    for d in dirs:
        d = os.path.abspath(d)
        if d and os.path.isdir(d) and d not in seen:
            seen.add(d)
            out.append(d)
    return out


def should_ignore(path):
    name = os.path.basename(path).lower()
    if name in IGNORE_NAMES or name.startswith('~') or name.startswith('_'):
        return True
    if name.endswith('.exe') or 'route_t&p.aiz' in name:
        return True
    return False


def process_export(path, state, on_log=None, on_success=None, silent=True):
    path = os.path.abspath(path)
    if should_ignore(path):
        return False
    sig = file_signature(path)
    if not sig or state['processed'].get(path) == sig:
        return False

    time.sleep(DEBOUNCE_SEC)
    sig2 = file_signature(path)
    if not sig2 or sig2 != sig:
        return False

    from generate_from_export import generate_from_export

    log('Processing ADC export: %s' % path, on_log)
    try:
        result = generate_from_export(path)
    except Exception as exc:
        log('FAILED: %s' % exc, on_log)
        return False

    state['processed'][path] = sig2
    save_state(state)
    log('OK: %d/%d notices -> %s' % (
        result['matched'], result['wanted'], result['output']), on_log)
    if on_success:
        on_success(result)
    return True


class RouteWatcher:
    """Управляемый watcher для вкладки «Маршрут»."""

    def __init__(self, on_log=None, on_success=None):
        self.on_log = on_log
        self.on_success = on_success
        self._stop = threading.Event()
        self._thread = None
        self._observer = None

    @property
    def running(self):
        return self._thread is not None and self._thread.is_alive()

    def start(self):
        if self.running:
            return
        self._stop.clear()
        paths = _paths()
        os.makedirs(paths['spool'], exist_ok=True)
        os.makedirs(os.path.dirname(paths['output_aiz']), exist_ok=True)
        cat = find_catalogue()
        log('Route watcher starting', self.on_log)
        if cat:
            log('Catalogue: %s' % cat, self.on_log)
        else:
            log('WARNING: catalogue not configured', self.on_log)
        log('Output: %s' % paths['output_aiz'], self.on_log)
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._observer:
            try:
                self._observer.stop()
                self._observer.join(timeout=3)
            except Exception:
                pass
            self._observer = None
        if self._thread:
            self._thread.join(timeout=4)
            self._thread = None
        log('Route watcher stopped', self.on_log)

    def _run(self):
        state = load_state()
        dirs = watch_directories()
        for d in dirs:
            log('Watching: %s' % d, self.on_log)
        try:
            self._run_watchdog(state, dirs)
        except ImportError:
            log('watchdog unavailable — poll mode', self.on_log)
            self._run_poll(state, dirs)

    def _run_watchdog(self, state, dirs):
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer

        watcher = self
        lock = threading.Lock()
        pending = {}

        def schedule(path):
            path = os.path.abspath(path)
            ext = os.path.splitext(path)[1].lower()
            if ext not in WATCH_EXTENSIONS:
                return
            with lock:
                if path in pending:
                    pending[path].cancel()
                timer = threading.Timer(DEBOUNCE_SEC, run_one, args=(path,))
                pending[path] = timer
                timer.start()

        def run_one(path):
            with lock:
                pending.pop(path, None)
            if os.path.isfile(path) and not watcher._stop.is_set():
                process_export(path, state, watcher.on_log, watcher.on_success)

        class Handler(FileSystemEventHandler):
            def on_created(self, event):
                if not event.is_directory:
                    schedule(event.src_path)

            def on_modified(self, event):
                if not event.is_directory:
                    schedule(event.src_path)

        observer = Observer()
        for d in dirs:
            try:
                observer.schedule(Handler(), d, recursive=True)
            except OSError as exc:
                log('Skip watch %s: %s' % (d, exc), self.on_log)
        observer.start()
        self._observer = observer
        while not self._stop.is_set():
            time.sleep(0.5)
        observer.stop()
        observer.join(timeout=3)

    def _run_poll(self, state, dirs):
        known = {}
        while not self._stop.is_set():
            for d in dirs:
                try:
                    for root, _, files in os.walk(d):
                        for name in files:
                            path = os.path.join(root, name)
                            ext = os.path.splitext(name)[1].lower()
                            if ext not in WATCH_EXTENSIONS:
                                continue
                            sig = file_signature(path)
                            if known.get(path) != sig:
                                known[path] = sig
                                process_export(
                                    path, state, self.on_log, self.on_success)
                except OSError:
                    pass
            time.sleep(1.5)
