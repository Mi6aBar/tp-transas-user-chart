# -*- coding: utf-8 -*-
"""ADC paths + portable app directory (config.json рядом с программой)."""
import json
import os
import subprocess
import sys
import winreg

REG_PATH = r'Software\WOW6432Node\ADMIRALTY Digital Catalogue'
CONFIG_NAME = 'config.json'
OUTPUT_DIR_NAME = 'Output'


def get_app_dir():
    """Папка portable-программы (рядом с .exe или T&P_Program при запуске из исходников)."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def config_file():
    return os.path.join(get_app_dir(), CONFIG_NAME)


def load_config():
    path = config_file()
    if os.path.isfile(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (OSError, ValueError):
            pass
    return {}


def save_config(data):
    path = config_file()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def read_adc_registry():
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, REG_PATH)
        install = winreg.QueryValueEx(key, 'InstallDir')[0]
        common = winreg.QueryValueEx(key, 'CommonDataDir')[0]
        return install.rstrip('\\/'), common.rstrip('\\/')
    except OSError:
        return None, None


def exe_from_install_dir(install_dir):
    if not install_dir:
        return None
    path = os.path.join(install_dir, 'bin', 'ADMIRALTYDigitalCatalogue.exe')
    if os.path.isfile(path):
        return os.path.abspath(path)
    return None


def catalogue_candidates(install_dir=None, common_dir=None):
    out = []
    if common_dir:
        out.extend([
            os.path.join(common_dir, 'tpnms', 'tpnms.xml'),
            os.path.join(common_dir, 'tpnms', 'tpnms.zip'),
            os.path.join(common_dir, 'catalogs', 'tpnms.zip'),
        ])
    if install_dir:
        out.extend([
            os.path.join(install_dir, 'catalogue', 'tpnms.zip'),
            os.path.join(install_dir, 'catalogue', 'tpnms.xml'),
        ])
    pf86 = os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)')
    out.append(os.path.join(pf86, 'ADMIRALTY_Digital_Catalogue', 'catalogue', 'tpnms.zip'))
    return out


def find_catalogue():
    cfg = load_config()
    path = cfg.get('catalogue_path')
    if path and os.path.isfile(path):
        return os.path.abspath(path)
    install_dir, common_dir = read_adc_registry()
    if cfg.get('adc_install_dir'):
        install_dir = cfg['adc_install_dir']
    if cfg.get('common_data_dir'):
        common_dir = cfg['common_data_dir']
    seen = set()
    for cand in catalogue_candidates(install_dir, common_dir):
        cand = os.path.abspath(cand)
        if cand in seen:
            continue
        seen.add(cand)
        if os.path.isfile(cand):
            return cand
    return None


def find_adc_exe():
    cfg = load_config()
    path = cfg.get('adc_exe')
    if path and os.path.isfile(path):
        return os.path.abspath(path)
    found = exe_from_install_dir(cfg.get('adc_install_dir'))
    if found:
        return found
    reg_install, _ = read_adc_registry()
    found = exe_from_install_dir(reg_install)
    if found:
        return found
    pf86 = os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)')
    for base in (pf86, os.environ.get('ProgramFiles', r'C:\Program Files')):
        found = exe_from_install_dir(os.path.join(base, 'ADMIRALTY_Digital_Catalogue'))
        if found:
            return found
    return None


def default_output_dir():
    cfg = load_config()
    out = cfg.get('output_dir')
    if out:
        out = os.path.abspath(out)
        os.makedirs(out, exist_ok=True)
        return out
    out = os.path.join(get_app_dir(), OUTPUT_DIR_NAME)
    os.makedirs(out, exist_ok=True)
    return out


def route_aiz_path():
    return os.path.join(default_output_dir(), 'Route_T&P.aiz')


def world_aiz_path():
    return os.path.join(default_output_dir(), 'T&P World.aiz')


def reveal_in_explorer(path):
    path = os.path.abspath(path)
    if not os.path.isfile(path):
        folder = path
        if os.path.isdir(folder):
            subprocess.Popen(['explorer', os.path.normpath(folder)])
        return
    subprocess.Popen(['explorer', '/select,', os.path.normpath(path)])


def detect_defaults():
    reg_install, reg_common = read_adc_registry()
    install_dir = reg_install or os.path.join(
        os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)'),
        'ADMIRALTY_Digital_Catalogue')
    catalogue = None
    for cand in catalogue_candidates(install_dir, reg_common):
        if os.path.isfile(cand):
            catalogue = os.path.abspath(cand)
            break
    app = get_app_dir()
    out = os.path.join(app, OUTPUT_DIR_NAME)
    return {
        'adc_install_dir': install_dir if os.path.isdir(install_dir) else '',
        'adc_exe': exe_from_install_dir(install_dir) or '',
        'common_data_dir': reg_common or '',
        'catalogue_path': catalogue or '',
        'output_dir': out,
        'route_output_path': os.path.join(out, 'Route_T&P.aiz'),
    }
