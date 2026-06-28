# T&P CHART MASTER

Portable Windows application for building **ECDIS user charts** from **ADMIRALTY T&P** notices via **ADC** (Transas, Furuno, JRC).

**Version:** 1.1

## Authors

| Role | Contact |
|------|---------|
| **Developer** | [t.me/mishabar](https://t.me/mishabar) |
| **Project** | [t.me/sea_apks](https://t.me/sea_apks) |

## Features

- **Route** — chart from ADC Print PDF (auto watcher + manual)
- **World** — worldwide chart from full T&P catalogue (`tpnms.xml` / `tpnms.zip`)
- **Notice list** — extract T&P notice IDs from PDF
- **ECDIS formats** — Transas `.aiz`, Furuno `.xml` (BETA / BETA2), JRC `.csv`
- **Portable** — single `TP_Chart_Master.exe`, no Python install required
- **Languages** — Русский / English

## Furuno export modes

| Mode | Use case |
|------|----------|
| **Furuno BETA** | Route charts aligned with ADC `Route TP` reference (areas + labels, 200 points/file) |
| **Furuno BETA2** | Route + world: lines + areas + labels (NAVAREA-style, 200 points/file) |

## Requirements

- Windows
- ADMIRALTY Digital Catalogue (ADC)
- T&P catalogue: `tpnms.xml` or `tpnms.zip`

## Download

Ready-to-use build: **[Releases](https://github.com/Mi6aBar/tp-transas-user-chart/releases)** — download `TP_Chart_Master.exe`.

## Run

1. Download `TP_Chart_Master.exe` (place in any folder)
2. Double-click to start
3. **Settings** — ADC folder, T&P catalogue, Output folder, ECDIS format
4. Use **Route**, **World**, or **Notice list** tabs

Results are saved to the **Output** folder next to the exe.

## Build from source

```bash
pip install pyinstaller pypdf watchdog pillow
python build.py
```

Output: `../T&P_Program_v1.1/TP_Chart_Master.exe`

## Project structure

```
tp_app.py          — GUI application
build.py           — PyInstaller build script
payload/           — core modules (export, watcher, i18n)
app_icon.png       — application icon source
TP_Transas.ico     — Windows icon
```

## Typical paths (ADC)

- ADC folder: `C:\Program Files (x86)\ADMIRALTY_Digital_Catalogue`
- T&P catalogue: `C:\ProgramData\ADMIRALTY_Digital_Catalogue\tpnms\tpnms.xml`

---

**T&P CHART MASTER** · Developer: [t.me/mishabar](https://t.me/mishabar) · Project: [t.me/sea_apks](https://t.me/sea_apks)
