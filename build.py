# -*- coding: utf-8 -*-
"""Сборка TP_Transas.exe в папку T&P_Program (только exe + README)."""
import os
import shutil
import subprocess
import sys

SRC_ROOT = os.path.dirname(os.path.abspath(__file__))
PAYLOAD = os.path.join(SRC_ROOT, 'payload')
BUILD = os.path.join(SRC_ROOT, 'build')
DIST = os.path.join(SRC_ROOT, 'dist')
RELEASE = os.path.join(os.path.dirname(SRC_ROOT), 'T&P_Program')
OUT_EXE = os.path.join(RELEASE, 'TP_Transas.exe')
ICON = os.path.join(SRC_ROOT, 'TP_Transas.ico')
ICON_PNG = os.path.join(SRC_ROOT, 'app_icon.png')

SRC_WORLD = os.path.join(os.path.dirname(SRC_ROOT), 't&p world project', 'generate_world_tpnm_aiz.py')
SRC_PARSE = os.path.join(os.path.dirname(SRC_ROOT), 'ADC_TPNM_Installer', 'payload', 'parse_adc_export.py')


def make_icon():
    if not os.path.isfile(ICON_PNG):
        return
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print('Pillow not installed — skip icon refresh')
        return
    img = Image.open(ICON_PNG).convert('RGBA')
    w, h = img.size
    radius = int(min(w, h) * 0.18)
    mask = Image.new('L', (w, h), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, w - 1, h - 1), radius=radius, fill=255)
    rounded = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    rounded.paste(img, (0, 0), mask)
    rounded.save(ICON_PNG)
    sizes = [
        (256, 256), (128, 128), (96, 96), (72, 72), (64, 64),
        (48, 48), (40, 40), (32, 32), (24, 24), (20, 20), (16, 16),
    ]
    rounded.save(ICON, format='ICO', sizes=sizes)
    print('Icon:', ICON, '(%d sizes, rounded)' % len(sizes))


def sync_payload():
    os.makedirs(PAYLOAD, exist_ok=True)
    shutil.copy2(SRC_WORLD, os.path.join(PAYLOAD, 'generate_world_tpnm_aiz.py'))
    shutil.copy2(SRC_PARSE, os.path.join(PAYLOAD, 'parse_adc_export.py'))


def clean_release_dir():
    os.makedirs(RELEASE, exist_ok=True)
    keep = {'TP_Transas.exe', 'README.txt'}
    for name in os.listdir(RELEASE):
        if name not in keep:
            path = os.path.join(RELEASE, name)
            if os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
            else:
                os.remove(path)


def main():
    sync_payload()
    make_icon()
    for d in (BUILD, DIST):
        if os.path.isdir(d):
            shutil.rmtree(d, ignore_errors=True)
    os.makedirs(DIST, exist_ok=True)

    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--noconfirm', '--clean',
        '--onefile', '--noconsole',
        '--name', 'TP_Transas',
        f'--paths={PAYLOAD}',
        f'--distpath={DIST}',
        f'--workpath={os.path.join(BUILD, "work")}',
        f'--specpath={BUILD}',
        '--hidden-import', 'adc_paths',
        '--hidden-import', 'generate_world_tpnm_aiz',
        '--hidden-import', 'generate_from_export',
        '--hidden-import', 'parse_adc_export',
        '--hidden-import', 'route_watcher',
        '--hidden-import', 'extract_notice_list',
        '--hidden-import', 'i18n',
        '--hidden-import', 'pypdf',
        '--hidden-import', 'watchdog',
        '--hidden-import', 'watchdog.observers',
        '--hidden-import', 'watchdog.events',
    ]
    if os.path.isfile(ICON):
        cmd.extend(['--icon', ICON])
        cmd.extend(['--add-data', ICON + os.pathsep + '.'])
        if os.path.isfile(ICON_PNG):
            cmd.extend(['--add-data', ICON_PNG + os.pathsep + '.'])
    cmd.append(os.path.join(SRC_ROOT, 'tp_app.py'))
    print('>>', ' '.join(cmd))
    subprocess.check_call(cmd, cwd=SRC_ROOT)

    built = os.path.join(DIST, 'TP_Transas.exe')
    if not os.path.isfile(built):
        raise SystemExit('Build failed')

    clean_release_dir()
    shutil.copy2(built, OUT_EXE)
    print('OK:', OUT_EXE, '(%d bytes)' % os.path.getsize(OUT_EXE))
    print('Release folder:', RELEASE)


if __name__ == '__main__':
    main()
