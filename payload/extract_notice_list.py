# -*- coding: utf-8 -*-
"""Extract unique T&P notice IDs from a document (ADC T&P List Helper logic)."""
import os
import re
import zipfile
import xml.etree.ElementTree as ET

NOTICE_PATTERN = re.compile(r'\d+\([A-Za-z]\)/(?:20\d{2}|\d{2})')
_W_NS = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


def _read_text_file(path):
    for enc in ('utf-8-sig', 'utf-8', 'cp1251', 'cp1252', 'latin-1'):
        try:
            with open(path, 'r', encoding=enc) as fh:
                return fh.read()
        except (UnicodeDecodeError, UnicodeError):
            continue
    with open(path, 'rb') as fh:
        return fh.read().decode('utf-8', errors='replace')


def _read_docx(path):
    with zipfile.ZipFile(path) as zf:
        xml = zf.read('word/document.xml')
    root = ET.fromstring(xml)
    parts = []
    for node in root.iter(_W_NS + 't'):
        if node.text:
            parts.append(node.text)
        if node.tail:
            parts.append(node.tail)
    return ''.join(parts)


def _read_pdf(path):
    from pypdf import PdfReader
    reader = PdfReader(path)
    return '\n'.join((page.extract_text() or '') for page in reader.pages)


def read_document_text(path, lang=None):
    ext = os.path.splitext(path)[1].lower()
    if ext == '.docx':
        return _read_docx(path)
    if ext == '.pdf':
        return _read_pdf(path)
    if ext == '.doc':
        from i18n import t
        raise ValueError(t('err_doc_format', lang))
    return _read_text_file(path)


def extract_notice_ids(text):
    seen = set()
    results = []
    for match in NOTICE_PATTERN.finditer(text):
        value = match.group(0)
        if value not in seen:
            seen.add(value)
            results.append(value)
    return results


def extract_notice_list(input_path, output_path=None, lang=None):
    from i18n import t
    input_path = os.path.abspath(input_path)
    if not os.path.isfile(input_path):
        raise FileNotFoundError(t('err_file_not_found', lang, path=input_path))

    text = read_document_text(input_path, lang)
    notices = extract_notice_ids(text)

    if output_path is None:
        stem = os.path.splitext(os.path.basename(input_path))[0]
        from adc_paths import default_output_dir
        output_path = os.path.join(default_output_dir(), stem + '_cleaned.txt')
    else:
        output_path = os.path.abspath(output_path)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8-sig', newline='\n') as fh:
        for line in notices:
            fh.write(line + '\n')

    return {
        'input': input_path,
        'output': output_path,
        'count': len(notices),
        'notices': notices,
    }
