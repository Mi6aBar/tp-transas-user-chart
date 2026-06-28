# -*- coding: utf-8 -*-
"""UI strings: Russian (default) and English."""
import locale
import sys

LANG_RU = 'ru'
LANG_EN = 'en'

DEFAULT_ADC_PATH = r'C:\Program Files (x86)\ADMIRALTY_Digital_Catalogue'
DEFAULT_CATALOGUE_PATH = r'C:\ProgramData\ADMIRALTY_Digital_Catalogue\tpnms\tpnms.xml'

LANG_LABELS = {
    LANG_RU: 'Русский',
    LANG_EN: 'English',
}

# Language names as shown in the combobox (depend on current UI language).
LANGUAGE_OPTIONS = {
    LANG_RU: {LANG_RU: 'Русский', LANG_EN: 'English'},
    LANG_EN: {LANG_RU: 'Russian', LANG_EN: 'English'},
}

CHART_FORMAT_CODES = ('transas', 'furuno', 'furuno_beta2', 'jrc')

CHART_FORMAT_LABELS = {
    LANG_RU: {
        'transas': 'Transas (.aiz)',
        'furuno': 'Furuno BETA (папка .xml)',
        'furuno_beta2': 'Furuno BETA2 (папка .xml)',
        'jrc': 'JRC JAN-7201/9201 (.csv)',
    },
    LANG_EN: {
        'transas': 'Transas (.aiz)',
        'furuno': 'Furuno BETA (.xml folder)',
        'furuno_beta2': 'Furuno BETA2 (.xml folder)',
        'jrc': 'JRC JAN-7201/9201 (.csv)',
    },
}

STRINGS = {
    LANG_RU: {
        'window_title': 'T&P CHART MASTER',
        'header': 'T&P CHART MASTER',
        'tab_settings': '  Настройки  ',
        'tab_route': '  Маршрут (Print PDF)  ',
        'tab_world': '  Весь мир  ',
        'tab_list': '  Список нотисов  ',
        'lbl_adc_dir': 'Папка ADC:',
        'lbl_catalogue': 'Каталог T&P:',
        'lbl_output': 'Папка Output:',
        'lbl_program_dir': 'Папка программы:',
        'lbl_language': 'Язык:',
        'lbl_chart_format': 'Формат ECDIS:',
        'btn_save_settings': 'Сохранить настройки',
        'settings_hint': (
            'Если при запуске программы пути к папкам не прописались автоматически:\n'
            'Папка ADC как правило имеет путь: {adc_path}\n'
            'Каталог T&P как правило имеет путь: {catalogue_path}'
        ),
        'route_steps': (
            '1. Запустите ADC по кнопке ниже\n'
            '2. Route → Load Route (пропустите шаг, если маршрут загружен)\n'
            '3. Нажмите T&P NMs\n'
            '4. Route → Route to Basket (вы увидите T&P список на ваш маршрут)\n'
            '5. Спускаемся в самый низ списка → View All\n'
            '6. Print → Print to PDF\n'
            '7. Выбираем место сохранения PDF и сохраняем документ\n'
            '8. Немного ждём, папка с файлом карты откроется автоматически'
        ),
        'world_info': (
            'Собрать user chart со всеми T&P нотисами из каталога ADC.\n'
            'Файл T&P World сохраняется в папку Output (формат — в настройках).'
        ),
        'list_info': 'Извлечь номера T&P нотисов из PDF документа.',
        'btn_launch_adc': 'Запустить ADC',
        'btn_build_pdf': 'Собрать из PDF',
        'btn_open_output': 'Открыть папку Output',
        'btn_build_world': 'Собрать мировую карту',
        'btn_pick_file': 'Выбрать файл',
        'dlg_adc_folder': 'Папка ADMIRALTY Digital Catalogue',
        'dlg_catalogue': 'Каталог T&P',
        'dlg_output_folder': 'Папка Output',
        'dlg_route_pdf': 'ADC T&P export (PDF)',
        'dlg_notice_pdf': 'PDF со списком нотисов',
        'filetype_catalogue': 'T&P catalogue',
        'filetype_pdf': 'PDF',
        'filetype_all': 'All',
        'msg_settings_saved': 'Настройки сохранены.',
        'msg_settings_saved_path': 'Настройки сохранены в\n{path}',
        'err_catalogue_missing': 'Укажите каталог tpnms.xml / tpnms.zip на вкладке «Настройки».',
        'err_adc_not_found': 'ADC не найден. Укажите папку ADC в настройках.',
        'warn_furuno_limit': (
            'Furuno: файл содержит {points} точек, лимит ECDIS — {limit}.\n'
            'Импорт, скорее всего, будет отклонён. Для маршрута используйте вкладку '
            '«Маршрут»; для полного мира — Transas, Furuno или JRC.'
        ),
        'info_furuno_split': (
            'Furuno: создано {files} user chart ({points} точек).\n'
            'Папка: {folder}\n'
            'На ECDIS: Manage Data → Data Import → User Chart → выберите эту папку.'
        ),
        'warn_furuno_skipped': (
            'Furuno: пропущено объектов: {skipped} (один объект > {limit} точек).'
        ),
        'warn_no_notices': 'Нотисы не найдены.',
        'warn_no_notices_pattern': 'В файле не найдено записей вида 1234(P)/2025.',
        'status_adc_started': 'ADC запущен.',
        'status_build_route': 'Сборка маршрута…',
        'status_route_updated': 'Route_T&P обновлён ({count} объектов)',
        'status_furuno_ready': 'Furuno: {files} user chart(s), {count} objects',
        'status_extracting': 'Извлечение списка…',
        'status_list_saved': 'Список сохранён: {count} нотисов',
        'status_build_world': 'Сборка мировой карты…',
        'status_world_ready': 'Мировая карта готова ({count} объектов).',
        'status_furuno_world': 'Furuno: {files} user chart(s), {count} objects',
        'status_build_error': 'Ошибка сборки.',
        'err_file_not_found': 'Файл не найден: {path}',
        'err_doc_format': 'Формат .doc не поддерживается. Сохраните файл как .docx или .txt.',
        'err_catalogue_not_found': 'Каталог T&P не найден: {path}',
        'err_no_notice_ids': 'В экспорте не найдены номера T&P нотисов: {path}',
        'err_notices_not_matched': 'В экспорте {count} ID, но ни один не найден в каталоге.',
        'err_input_not_found': 'Входной файл не найден: {path}',
        'err_unknown_format': 'Неизвестный формат карты: {format}',
        'auth_by': 'By',
        'auth_dev': 'mishabar',
        'auth_channel': 't.me/sea_apks',
    },
    LANG_EN: {
        'window_title': 'T&P CHART MASTER',
        'header': 'T&P CHART MASTER',
        'tab_settings': '  Settings  ',
        'tab_route': '  Route (Print PDF)  ',
        'tab_world': '  World  ',
        'tab_list': '  Notice list  ',
        'lbl_adc_dir': 'ADC folder:',
        'lbl_catalogue': 'T&P catalogue:',
        'lbl_output': 'Output folder:',
        'lbl_program_dir': 'Program folder:',
        'lbl_language': 'Language:',
        'lbl_chart_format': 'ECDIS format:',
        'btn_save_settings': 'Save settings',
        'settings_hint': (
            'If folder paths were not filled in automatically at startup:\n'
            'ADC folder is usually: {adc_path}\n'
            'T&P catalogue is usually: {catalogue_path}'
        ),
        'route_steps': (
            '1. Start ADC using the button below\n'
            '2. Route → Load Route (skip if the route is already loaded)\n'
            '3. Click T&P NMs\n'
            '4. Route → Route to Basket (you will see the T&P list for your route)\n'
            '5. Scroll to the bottom of the list → View All\n'
            '6. Print → Print to PDF\n'
            '7. Choose where to save the PDF and save the document\n'
            '8. Wait a moment — the folder with the chart file will open automatically'
        ),
        'world_info': (
            'Build a user chart with all T&P notices from the ADC catalogue.\n'
            'T&P World is saved to the Output folder (format is set in Settings).'
        ),
        'list_info': 'Extract T&P notice numbers from a PDF document.',
        'btn_launch_adc': 'Start ADC',
        'btn_build_pdf': 'Build from PDF',
        'btn_open_output': 'Open Output folder',
        'btn_build_world': 'Build world chart',
        'btn_pick_file': 'Choose file',
        'dlg_adc_folder': 'ADMIRALTY Digital Catalogue folder',
        'dlg_catalogue': 'T&P catalogue',
        'dlg_output_folder': 'Output folder',
        'dlg_route_pdf': 'ADC T&P export (PDF)',
        'dlg_notice_pdf': 'PDF with notice list',
        'filetype_catalogue': 'T&P catalogue',
        'filetype_pdf': 'PDF',
        'filetype_all': 'All',
        'msg_settings_saved': 'Settings saved.',
        'msg_settings_saved_path': 'Settings saved to\n{path}',
        'err_catalogue_missing': 'Specify tpnms.xml / tpnms.zip on the Settings tab.',
        'err_adc_not_found': 'ADC not found. Specify the ADC folder in Settings.',
        'warn_furuno_limit': (
            'Furuno: this file has {points} points; ECDIS limit is {limit}.\n'
            'Import will likely be rejected. Use the Route tab for route charts; '
            'use Transas, Furuno or JRC for the full worldwide catalogue.'
        ),
        'info_furuno_split': (
            'Furuno: {files} user chart(s) created ({points} points).\n'
            'Folder: {folder}\n'
            'On ECDIS: Manage Data → Data Import → User Chart → select this folder.'
        ),
        'warn_furuno_skipped': (
            'Furuno: skipped {skipped} object(s) (single object exceeds {limit} points).'
        ),
        'warn_no_notices': 'No notices found.',
        'warn_no_notices_pattern': 'No entries like 1234(P)/2025 were found in the file.',
        'status_adc_started': 'ADC started.',
        'status_build_route': 'Building route…',
        'status_route_updated': 'Route_T&P updated ({count} objects)',
        'status_furuno_ready': 'Furuno: {files} user chart(s), {count} objects',
        'status_extracting': 'Extracting list…',
        'status_list_saved': 'List saved: {count} notices',
        'status_build_world': 'Building world chart…',
        'status_world_ready': 'World chart ready ({count} objects).',
        'status_furuno_world': 'Furuno: {files} user chart(s), {count} objects',
        'status_build_error': 'Build failed.',
        'err_file_not_found': 'File not found: {path}',
        'err_doc_format': 'The .doc format is not supported. Save the file as .docx or .txt.',
        'err_catalogue_not_found': 'T&P catalogue not found: {path}',
        'err_no_notice_ids': 'No T&P notice IDs found in export: {path}',
        'err_notices_not_matched': 'Export has {count} IDs but none matched the catalogue.',
        'err_input_not_found': 'Input file not found: {path}',
        'err_unknown_format': 'Unknown chart format: {format}',
        'auth_by': 'By',
        'auth_dev': 'mishabar',
        'auth_channel': 't.me/sea_apks',
    },
}


def detect_system_language():
    if sys.platform == 'win32':
        try:
            import ctypes
            lang_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            if (lang_id & 0x3FF) == 0x09:
                return LANG_EN
        except Exception:
            pass
    try:
        loc = locale.getdefaultlocale()[0] or ''
        if loc.lower().startswith('en'):
            return LANG_EN
    except Exception:
        pass
    return LANG_RU


def resolve_language(cfg=None):
    if cfg is None:
        from adc_paths import load_config
        cfg = load_config()
    lang = cfg.get('ui_language')
    if lang in (LANG_RU, LANG_EN):
        return lang
    return detect_system_language()


def language_option_labels(ui_lang=None):
    if ui_lang is None:
        ui_lang = resolve_language()
    return LANGUAGE_OPTIONS.get(ui_lang, LANGUAGE_OPTIONS[LANG_EN])


def lang_code_to_label(code, ui_lang=None):
    return language_option_labels(ui_lang).get(code, language_option_labels(LANG_EN)[LANG_EN])


def label_to_lang_code(label, ui_lang=None):
    for labels in (language_option_labels(ui_lang), LANGUAGE_OPTIONS[LANG_RU], LANGUAGE_OPTIONS[LANG_EN]):
        for code, name in labels.items():
            if name == label:
                return code
    return LANG_EN if ui_lang == LANG_EN else LANG_RU


def chart_format_labels(lang=None):
    if lang is None:
        lang = resolve_language()
    return CHART_FORMAT_LABELS.get(lang, CHART_FORMAT_LABELS[LANG_RU])


def chart_code_to_label(code, lang=None):
    return chart_format_labels(lang).get(code, chart_format_labels(lang)['transas'])


def label_to_chart_code(label, lang=None):
    labels = chart_format_labels(lang)
    for code, name in labels.items():
        if name == label:
            return code
    return 'transas'


def t(key, lang=None, **kwargs):
    if lang is None:
        lang = resolve_language()
    text = STRINGS.get(lang, {}).get(key)
    if text is None and lang != LANG_EN:
        text = STRINGS[LANG_EN].get(key)
    if text is None:
        text = key
    if kwargs:
        return text.format(**kwargs)
    return text


def localize_error(message, lang=None):
    """Map common backend errors to translated UI strings."""
    if lang is None:
        lang = resolve_language()
    import re
    m = re.match(r'T&P catalogue not found: (.+)$', message)
    if m:
        return t('err_catalogue_not_found', lang, path=m.group(1))
    m = re.match(r'No T&P notice IDs found in export: (.+)$', message)
    if m:
        return t('err_no_notice_ids', lang, path=m.group(1))
    m = re.match(r'Export has (\d+) IDs but none matched catalogue$', message)
    if m:
        return t('err_notices_not_matched', lang, count=m.group(1))
    m = re.match(r'Input not found: (.+)$', message)
    if m:
        return t('err_input_not_found', lang, path=m.group(1))
    m = re.match(r'Unknown chart format: (.+)$', message)
    if m:
        return t('err_unknown_format', lang, format=m.group(1))
    return message
