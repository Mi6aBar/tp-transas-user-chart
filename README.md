# T&P — TRANSAS USER CHART

Portable Windows application for building **Transas user chart** (`.aiz`) from **ADMIRALTY T&P** notices via **ADC**.

**Version:** 1.0

## Authors

| Role | Contact |
|------|---------|
| **Developer** | [t.me/mishabar](https://t.me/mishabar) |
| **Project** | [t.me/sea_apks](https://t.me/sea_apks) |

## Features

- **Route** — `Route_T&P.aiz` from ADC Print PDF (auto + manual)
- **World** — `T&P World.aiz` from full T&P catalogue
- **Notice list** — extract notice numbers from PDF
- **Portable** — single `TP_Transas.exe`, no Python install required
- **Languages** — Русский / English

## Requirements

- Windows
- ADMIRALTY Digital Catalogue (ADC)
- T&P catalogue: `tpnms.xml` or `tpnms.zip`

## Download

Ready-to-use build: **[Releases](https://github.com/Mi6aBar/tp-transas-user-chart/releases)** — download `TP_Transas.exe`.

## Run

1. Download `TP_Transas.exe`
2. Double-click to start
3. **Settings** — set ADC folder, T&P catalogue, Output folder
4. Use **Route**, **World**, or **Notice list** tabs

Results are saved to the **Output** folder next to the exe.

Load `.aiz` in Transas MAPS: **User chart**

## Build from source

```bash
pip install pyinstaller pypdf watchdog pillow
python build.py
```

Output: `../T&P_Program/TP_Transas.exe`

## Project structure

```
tp_app.py          — GUI application
build.py           — PyInstaller build script
payload/           — core modules (.aiz generation, watcher, i18n)
app_icon.png       — application icon source
TP_Transas.ico     — Windows icon
```

## Typical paths (ADC)

- ADC folder: `C:\Program Files (x86)\ADMIRALTY_Digital_Catalogue`
- T&P catalogue: `C:\ProgramData\ADMIRALTY_Digital_Catalogue\tpnms\tpnms.xml`

---

**T&P — TRANSAS USER CHART** · Developer: [t.me/mishabar](https://t.me/mishabar) · Project: [t.me/sea_apks](https://t.me/sea_apks)
