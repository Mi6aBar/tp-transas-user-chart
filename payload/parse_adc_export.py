# -*- coding: utf-8 -*-
"""Parse notice IDs from ADC T&P print/export (PDF, HTML, plain text)."""
import os
import re

NOTICE_ID_RE = re.compile(r'\b(\d+\([TP]\)/\d+)\b', re.I)
PRIMARY_LINE_RE = re.compile(r'^(\d+\([TP]\)/\d+)\s+\S', re.I)

ADC_MARKERS = (
    'Charts affected',
    'Source:',
    'WGS84',
    'AUSTRALIA',
    'UNITED KINGDOM',
    'T&P NMs',
    'T&P NMs Message',
)


def normalize_notice_id(nid):
    return nid.upper().replace(' ', '')


def parse_primary_notice_ids(text):
    ids = set()
    for line in text.splitlines():
        line = line.strip().replace('\u00a0', ' ')
        if not line or line.lower().startswith('source:'):
            continue
        m = PRIMARY_LINE_RE.match(line)
        if m:
            ids.add(normalize_notice_id(m.group(1)))
    return ids


def is_adc_tp_export(text):
    primary = parse_primary_notice_ids(text)
    if not primary:
        all_ids = {normalize_notice_id(x) for x in NOTICE_ID_RE.findall(text)}
        if len(all_ids) < 2:
            return False
        primary = all_ids
    if any(marker in text for marker in ADC_MARKERS):
        return True
    return len(primary) >= 2


def read_text_export(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in ('.html', '.htm'):
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()
    if ext == '.pdf':
        try:
            import pypdf
        except ImportError:
            raise RuntimeError('pypdf required for PDF: pip install pypdf')
        reader = pypdf.PdfReader(path)
        return '\n'.join(page.extract_text() or '' for page in reader.pages)
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        return f.read()


def parse_adc_export(path):
    text = read_text_export(path)
    if not is_adc_tp_export(text):
        return set()
    return parse_primary_notice_ids(text) or {
        normalize_notice_id(x) for x in NOTICE_ID_RE.findall(text)
    }
