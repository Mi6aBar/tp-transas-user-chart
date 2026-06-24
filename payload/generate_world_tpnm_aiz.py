# -*- coding: utf-8 -*-
"""
Generate a Transas user chart (.aiz) with worldwide ADMIRALTY T&P notices
from the ADC weekly catalogue data (tpnms.zip / tpnms.xml).

Coordinates are taken from structured XML fields (no text scraping).
Consecutive positions with no text between them form a "run":
  - runs of 3+ positions become closed polygon objects (areas, cable routes)
  - shorter runs become individual point objects

Usage:
  python generate_world_tpnm_aiz.py [input tpnms.zip|tpnms.xml] [-o output.aiz]

Binary record layout was reverse-engineered from an original Transas
user chart and is identical to the one used in "t&p project".
"""
import argparse
import base64
import io
import os
import re
import struct
import sys
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

DEFAULT_INPUTS = [
    os.path.join(SCRIPT_DIR, 'tpnms.zip'),
    os.path.join(SCRIPT_DIR, 'tpnms.xml'),
    os.path.join(SCRIPT_DIR, '..', 't&p project', 'ADC_Full_WK23_26', 'catalogue', 'tpnms.zip'),
]

# ---------------------------------------------------------------------------
# Binary format (verified against original Transas user chart records)
# ---------------------------------------------------------------------------

# Static 299-byte chart header + 4 constant bytes (tail of data_state_id GUID)
STATIC_HEADER_B64 = (
    "KwEAAMpDaGFydCBIZWFkZXIAHQEAAAkAAAAsAAAASgAAAGsAAACPAAAAmgAAAKoAAAC6AAAA2AAAAPkAAADBcm9vdF9pZAAAEAAA"
    "AGvBB9n+dp1PqDFFjxz97HDBdmVyc2lvbl9pZAAAEAAAADzxtjBkyO5Hq4cOfwjN5RfBZGF0YV9zdGF0ZV9pZAAAEAAAAHQTuRhJ"
    "Us5Dg49VrwO48SHIQ29tbWVudAAAAMNEYW5nZXJGbGFnAAAAAADHZm9ybWF0AEFkZEluZm8AwXJvb3RfaWQAABAAAABrwQfZ/nad"
    "T6gxRY8c/exwwXZlcnNpb25faWQAABAAAAA88bYwZMjuR6uHDn8IzeUXwWRhdGFfc3RhdGVfaWQAABAAAAB0E7kYSVLOQ4OPVa8="
)

# Point record header template, 88 bytes (geometry type 3):
#   @2 u32 total length, @13 u8 const 0x58, @14 u32 vertex count (1),
#   @18 u32 coords offset,
#   directory entries: title @47, body @54, TS1 @61, TS2 @68, coords-2 @75
POINT_HDR = bytes([
    0x04, 0x00, 0x00, 0x00, 0x00, 0x00, 0x03, 0x00, 0x00, 0x00, 0x0E, 0xC0, 0x00, 0x58, 0x01, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x08, 0x00, 0x02, 0x00, 0x50, 0x00, 0x00, 0x00, 0x05, 0x08,
    0x00, 0x0B, 0x00, 0x00, 0x00, 0x04, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x04, 0x00, 0x58,
    0x00, 0x00, 0x00, 0x07, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x07, 0x09, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x06, 0x0D, 0x00, 0x00, 0x00, 0x00, 0x00, 0x06, 0x05, 0x00, 0x00, 0x00, 0x00, 0x00, 0x07,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
])

# Polygon record header template, 95 bytes (geometry type 4):
#   @2 u32 total length, @13 u8 const 0x50, @14 u32 vertex count,
#   @18 u32 coords offset, @26 u32 area fill style (directory tag 7:
#   5 = plain outline, 7 = hatched fill),
#   directory: title @54, body @61, TS1 @68, TS2 @75, coords-2 @82
# Area fill style written to directory tag 7 (@26) of polygon records.
POLY_FILL_HATCHED = 7
POLY_FILL_OUTLINE = 5

POLY_HDR = bytes([
    0x04, 0x00, 0x00, 0x00, 0x00, 0x00, 0x04, 0x00, 0x00, 0x00, 0x0E, 0x80, 0x00, 0x50, 0x05, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x09, 0x00, 0x07, 0x00, 0x00, 0x00, 0x00, 0x00, 0x04, 0x02,
    0x00, 0x57, 0x00, 0x00, 0x00, 0x05, 0x08, 0x00, 0x0B, 0x00, 0x00, 0x00, 0x04, 0x01, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x01, 0x04, 0x00, 0x5F, 0x00, 0x00, 0x00, 0x07, 0x03, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x07, 0x09, 0x00, 0x00, 0x00, 0x00, 0x00, 0x06, 0x0D, 0x00, 0x00, 0x00, 0x00, 0x00, 0x06,
    0x05, 0x00, 0x00, 0x00, 0x00, 0x00, 0x07, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
])


def build_record(title, body, coords, ts_bytes, fill_style=POLY_FILL_HATCHED, danger=None):
    """Build one chart record. danger: None | 'point' | 'zone' | 'line'."""
    is_poly = len(coords) > 1
    title_b = title.encode('utf-16-le') + b'\x00\x00'
    body_b = body.encode('utf-16-le') + b'\x00\x00'

    if danger == 'point':
        hdr_len = 135
        hdr = bytearray(base64.b64decode(DANGER_POINT_HDR_B64))
    elif danger == 'zone':
        hdr_len = 102
        hdr = bytearray(base64.b64decode(DANGER_ZONE_HDR_B64))
    elif danger == 'line':
        hdr_len = 95
        hdr = bytearray(base64.b64decode(DANGER_LINE_HDR_B64))
    else:
        hdr_len = 95 if is_poly else 88
        hdr = bytearray(POLY_HDR if is_poly else POINT_HDR)

    body_off = hdr_len + len(title_b)
    end_text = body_off + len(body_b)
    ts1 = end_text + 1
    ts2 = ts1 + 15
    coords_off = ts2 + 15 + 2
    total = coords_off + 8 * len(coords)

    struct.pack_into('<I', hdr, 2, total)
    struct.pack_into('<I', hdr, 14, len(coords))
    struct.pack_into('<I', hdr, 18, coords_off)
    if is_poly and not danger:
        struct.pack_into('<I', hdr, 26, fill_style)
    patch_dir_tag(hdr, 4, hdr_len)
    patch_dir_tag(hdr, 3, body_off)
    patch_dir_tag(hdr, 9, ts1)
    patch_dir_tag(hdr, 13, ts2)
    patch_dir_tag(hdr, 5, coords_off - 2)

    out = bytearray()
    out += hdr
    out += title_b
    out += body_b
    out += b'\x00'
    out += ts_bytes
    out += ts_bytes
    out += b'\x00\x00'
    for raw_lat, raw_lon in coords:
        out += struct.pack('<ii', raw_lat, raw_lon)
    return bytes(out)


def assemble_ai(records, has_danger=False):
    """Assemble the inner .ai file from a list of record byte strings."""
    static = static_header(has_danger)
    assert len(static) == 299

    records_blob = bytearray()
    offsets = []
    for rec in records:
        offsets.append(len(records_blob))
        records_blob += rec

    ai = bytearray()
    ai += static
    ai += struct.pack('<I', 0x21F1B803)        # constant bytes at 299
    ai += struct.pack('<I', len(records_blob))  # records block size
    ai += records_blob

    # trailer index block
    ai += struct.pack('<6I', 1, 0, 3, 4, len(records), 4)
    for off in offsets:
        ai += struct.pack('<I', off)
    for i in range(1, len(records) + 1):
        ai += struct.pack('<I', i)
    return bytes(ai)


# ---------------------------------------------------------------------------
# XML parsing
# ---------------------------------------------------------------------------

def parse_coordinate(loc):
    """Parse a <location> element. Returns (lat, lon, display_text) or None."""
    lat_el = loc.find('latitude')
    lon_el = loc.find('longitude')
    if lat_el is None or lon_el is None:
        return None

    def num(el, tag):
        # strip markers like '*' (new/revised entry) around numeric values
        return re.sub(r'[^0-9]', '', el.findtext(tag) or '')

    def axis(el):
        deg = num(el, 'degrees')
        minutes = num(el, 'minutes')
        decimals = num(el, 'decimals')
        seconds = num(el, 'seconds')
        hemi = re.sub(r'[^A-Z]', '', (el.findtext('hemisphere') or '').upper())
        if not deg or not minutes or hemi not in ('N', 'S', 'E', 'W'):
            return None
        d = float(deg)
        m = float(minutes)
        if decimals:
            m += float(decimals) / (10 ** len(decimals))
            text = "%s\xB0 %s.%s'%s" % (deg, minutes, decimals, hemi)
        elif seconds:
            m += float(seconds) / 60.0
            text = "%s\xB0 %s'%s\"%s" % (deg, minutes, seconds, hemi)
        else:
            text = "%s\xB0 %s'%s" % (deg, minutes, hemi)
        value = d + m / 60.0
        if hemi in ('S', 'W'):
            value = -value
        return value, text

    lat = axis(lat_el)
    lon = axis(lon_el)
    if lat is None or lon is None:
        return None
    return lat[0], lon[0], lat[1] + '., ' + lon[1] + '.'


class NoticeRenderer:
    """Flattens notice content to text in document order, recording each
    coordinate together with its position in the text (for run grouping)."""

    def __init__(self):
        self.parts = []
        self.length = 0
        # each coord: (text_pos, lat, lon, display, connectable)
        self.coords = []
        # >0 while inside a multi-column table whose rows hold several
        # coordinates side by side (separate zones, must not be connected)
        self.no_connect_depth = 0

    def emit(self, text):
        if text:
            self.parts.append(text)
            self.length += len(text)

    @staticmethod
    def is_multicolumn_coord_table(table):
        """True if any row of this table contains 2+ coordinates, i.e. the
        positions are laid out in parallel columns rather than a single list."""
        for tr in table.iter('TR'):
            if sum(1 for _ in tr.iter('location')) >= 2:
                return True
        return False

    def walk(self, el):
        tag = el.tag
        if tag == 'location':
            parsed = parse_coordinate(el)
            if parsed is not None:
                lat, lon, disp = parsed
                self.coords.append((self.length, lat, lon, disp,
                                    self.no_connect_depth == 0))
                self.emit(disp)
            return  # children already consumed
        if tag == 'graphic':
            self.emit('[see diagram]')
            return

        multicol = tag == 'TABLE' and self.is_multicolumn_coord_table(el)
        if multicol:
            self.no_connect_depth += 1

        self.emit(el.text or '')
        for child in el:
            if child.tag == 'TD':
                self.walk(child)
                self.emit('  ')
            else:
                self.walk(child)
            self.emit(child.tail or '')
        if tag in ('paragraph', 'TR', 'list_item'):
            self.emit('\n')

        if multicol:
            self.no_connect_depth -= 1

    def text(self):
        return ''.join(self.parts)


GAP_CLEAN = re.compile(r'[\s\.,;]+')


def group_runs(rendered_text, coords):
    """Group coordinates into runs of consecutive positions.
    Coordinates flagged as non-connectable (from multi-column tables) always
    form their own singleton run, so unrelated zones are never joined."""
    runs = []
    current = None
    prev_end = None
    for pos, lat, lon, disp, connectable in coords:
        new_run = True
        if connectable and current is not None and prev_end is not None:
            gap = rendered_text[prev_end:pos]
            if GAP_CLEAN.sub('', gap) == '':
                new_run = False
        if new_run:
            current = []
            runs.append(current)
        current.append((lat, lon, disp))
        prev_end = pos + len(disp)
        if not connectable:
            current = None  # force a fresh run for the next coordinate
    return runs


# Notices describing a linear feature: the coordinates form an open route
# (a line) rather than a closed area, so we must not close or fill them.
ROUTE_KEYWORDS = re.compile(
    r'(?i)\b(submarine cable|submarine power cable|fibre optic|fiber optic|'
    r'cable|pipeline|pipe-line|joining the following|route)\b')

DANGER_NON_RE = re.compile(r'(?i)\bnon[- ]dangerous\b')
DANGER_WRECK_FT = re.compile(r'(?i)^Wrecks?$')
DANGER_AREA_FT = re.compile(
    r'(?i)^(Restricted areas?|Danger area|Military practice areas?|'
    r'Explosive dumping grounds?|Prohibited areas?|Exclusion zones?)$')
DANGER_WRECK_TEXT = re.compile(r'(?i)\bdangerous wrecks?\b')
DANGER_AREA_TEXT = re.compile(
    r'(?i)\b(restricted areas?|danger areas?|prohibited areas?|'
    r'exclusion zones?|explosive dumping|military practice areas?|'
    r'no entry zones?|areas? (?:are )?prohibited)\b')

DANGER_POINT_HDR_B64 = (
    'BADNAAAAAQAAAA7AAFgBAAAAxQAAAAoABgBeAAAABgcANgAAAAQCAH8AAAAFCAABAAAABAEAAQAAAAEEAIcAAAAHAwCjAAAABwkApQAAAAYNALQAAAAGBQDDAAAAB2ZjN2Q5NjMzOGNiYTQwZWRhNTQyZTA1YTA1MWNjMGU4AAAAAAAAAAAA')
DANGER_ZONE_HDR_B64 = (
    'BADIAAAABAAAAA6AAFAFAAAAoAAAAAoABwAAAAAABBAAAAAAAAQCAF4AAAAFCAALAAAABAEAAQAAAAEEAGYAAAAHAwB+AAAABwkAgAAAAAYNAI8AAAAGBQCeAAAABwAAAAAAAAAA')
DANGER_LINE_HDR_B64 = (
    'BAC5AAAABAAAAA6AAFAEAAAAmQAAAAkABwAAAAAABAIAVwAAAAUIAAsAAAAEAQABAAAAAQQAXwAAAAcDAHcAAAAHCQB5AAAABg0AiAAAAAYFAJcAAAAHAAAAAAAAAAA=')


def static_header(has_danger=False):
    hdr = bytearray(base64.b64decode(STATIC_HEADER_B64))
    if has_danger:
        idx = hdr.find(b'DangerFlag')
        if idx >= 0:
            struct.pack_into('<I', hdr, idx + 11, 1)
    return bytes(hdr)


def patch_dir_tag(hdr, tag, value):
    pos = 22
    nfields = struct.unpack_from('<H', hdr, pos)[0]
    pos += 2
    for _ in range(nfields):
        if hdr[pos] == tag:
            struct.pack_into('<I', hdr, pos + 2, value)
            return True
        pos += 7
    return False


def notice_combined_text(notice):
    return '%s\n%s' % (notice.get('title', ''), notice.get('body', ''))


def is_non_danger_notice(notice):
    return bool(DANGER_NON_RE.search(notice_combined_text(notice)))


def classify_record_danger(notice, is_poly, is_route):
    if is_non_danger_notice(notice):
        return None
    features = notice.get('features') or []
    text = notice_combined_text(notice)
    if not is_poly:
        if any(DANGER_WRECK_FT.match(f) for f in features):
            return 'point'
        if DANGER_WRECK_TEXT.search(text):
            return 'point'
        if re.search(r'(?i)\bdangerous\b', text) and re.search(
                r'(?i)\b(wreck|obstruction|hazard)\b', text):
            return 'point'
        return None
    if is_route:
        if any(DANGER_AREA_FT.match(f) for f in features):
            return 'line'
        if DANGER_AREA_TEXT.search(text):
            return 'line'
        return None
    if any(DANGER_AREA_FT.match(f) for f in features):
        return 'zone'
    if DANGER_AREA_TEXT.search(text):
        return 'zone'
    if any(DANGER_WRECK_FT.match(f) for f in features):
        return 'zone'
    return None


def is_route(title, body):
    """True if the notice describes a cable/pipeline/route (open polyline)."""
    return bool(ROUTE_KEYWORDS.search(title) or ROUTE_KEYWORDS.search(body))


def clean_text(s):
    s = re.sub(r'[ \t]+', ' ', s)
    s = re.sub(r' ?\n ?', '\n', s)
    s = re.sub(r'\n{3,}', '\n\n', s)
    return s.strip()


def parse_notices(xml_bytes):
    root = ET.fromstring(xml_bytes)
    pub_date = root.get('date', '')
    notices = []

    for section in root.findall('geographical_section'):
        geo_el = section.find('geographical_area')
        geo_name = (geo_el.text or '').strip() if geo_el is not None else ''

        for n in section:
            if n.tag not in ('temporary', 'preliminary'):
                continue
            kind = 'T' if n.tag == 'temporary' else 'P'
            nid = '%s(%s)/%s' % (n.get('nm_number', '?'), kind, n.get('year', '?'))

            region = (n.findtext('region') or '').strip()
            sub_region = (n.findtext('sub_region') or '').strip()
            vicinities = [v.text.strip() for v in n.findall('.//vicinity')
                          if v.text and v.text.strip()]
            features = [f.text.strip() for f in n.findall('.//feature_type')
                        if f.text and f.text.strip()]
            authority = (n.findtext('authority') or '').strip()

            title_line = ' - '.join(x for x in [
                region, sub_region, ', '.join(vicinities)] if x)
            if features:
                title_line += ' - ' + '. '.join(features) + '.'

            charts = []
            for cn in n.findall('.//chart_number'):
                num = ((cn.findtext('prefix') or '') +
                       (cn.findtext('infix') or '') +
                       (cn.findtext('suffix') or '')).strip()
                if num:
                    charts.append(num)

            renderer = NoticeRenderer()
            ol = n.find('ordered_list')
            if ol is not None:
                renderer.walk(ol)
            body = clean_text(renderer.text())
            if charts:
                body += '\nCharts affected - ' + ' - '.join(charts)

            runs = group_runs(renderer.text(), renderer.coords)
            areas = [r for r in runs if len(r) >= 3]
            points = [c for r in runs if len(r) < 3 for c in r]
            if not areas and not points:
                continue

            notices.append({
                'id': nid,
                'geo': geo_name,
                'title': title_line,
                'authority': authority,
                'body': body,
                'features': features,
                'areas': areas,
                'points': points,
            })

    return pub_date, notices


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def to_raw(value):
    return int(round(value * 360000.0))


def load_tpnms_bytes(path):
    path = os.path.abspath(path)
    if path.lower().endswith('.zip'):
        with zipfile.ZipFile(path) as z:
            name = next(n for n in z.namelist() if n.lower().endswith('.xml'))
            return z.read(name)
    with open(path, 'rb') as f:
        return f.read()


def build_records_for_notices(notices, ts_bytes, log=None):
    """Собрать бинарные records для списка notices. Возвращает (records, stats, has_danger)."""
    records = []
    stats = {'areas': 0, 'lines': 0, 'points': 0, 'danger': 0}
    has_danger = False
    total = len(notices)
    for ni, n in enumerate(notices, 1):
        if log and (ni == 1 or ni % 250 == 0 or ni == total):
            log('Building records… %d / %d notices' % (ni, total))
        total_areas = len(n['areas'])
        total_pts = len(n['points'])
        multi = (total_areas + total_pts) > 1
        route = is_route(n['title'], n['body'])
        header_lines = '%s\nSource: %s\nGeo area: %s\n\n' % (n['title'], n['authority'], n['geo'])

        for ai, run in enumerate(n['areas'], 1):
            kind = 'Line' if route else 'Area'
            suffix = ' %s %d/%d' % (kind, ai, total_areas) if multi else ''
            title = n['id'] + suffix
            verts = [(to_raw(lat), to_raw(lon)) for lat, lon, _ in run]
            if route:
                fill = POLY_FILL_OUTLINE
                descr = 'Route of %d positions' % len(run)
                stats['lines'] += 1
            else:
                if verts[0] != verts[-1]:
                    verts.append(verts[0])
                fill = POLY_FILL_HATCHED
                descr = 'Area of %d positions' % len(run)
                stats['areas'] += 1
            danger = classify_record_danger(n, is_poly=True, is_route=route)
            if danger:
                has_danger = True
                stats['danger'] += 1
            body = ('%s\r\nNotice: %s%s\r\n\r\n%s%s'
                    % (descr, n['id'], suffix, header_lines, n['body'])).replace('\n', '\r\n').replace('\r\r', '\r')
            records.append(build_record(title, body, verts, ts_bytes, fill, danger=danger))

        for pi, (lat, lon, disp) in enumerate(n['points'], 1):
            suffix = ' Pt %d/%d' % (pi, total_pts) if multi else ''
            title = n['id'] + suffix
            danger = classify_record_danger(n, is_poly=False, is_route=False)
            if danger:
                has_danger = True
                stats['danger'] += 1
            body = ('Position: %s\r\nNotice: %s%s\r\n\r\n%s%s'
                    % (disp, n['id'], suffix, header_lines, n['body'])).replace('\n', '\r\n').replace('\r\r', '\r')
            records.append(build_record(title, body, [(to_raw(lat), to_raw(lon))], ts_bytes, danger=danger))
            stats['points'] += 1

    return records, stats, has_danger


def write_aiz_file(records, output_path, has_danger=False, log=None):
    if log:
        log('Packing .aiz…')
    ai_bytes = assemble_ai(records, has_danger=has_danger)
    if log:
        log('AI file size: %d bytes.' % len(ai_bytes))
    os.makedirs(os.path.dirname(os.path.abspath(output_path)) or '.', exist_ok=True)
    if os.path.exists(output_path):
        os.remove(output_path)
    entry_name = os.path.splitext(os.path.basename(output_path))[0] + '.ai'
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr(entry_name, ai_bytes)
    return len(ai_bytes)


def build_route_aiz(export_path, catalogue_path, output_path, log=None):
    """Маршрут: нотисы из ADC Print PDF/HTML -> .aiz."""
    from parse_adc_export import normalize_notice_id, parse_adc_export

    if log is None:
        log = print
    export_path = os.path.abspath(export_path)
    catalogue_path = os.path.abspath(catalogue_path)
    output_path = os.path.abspath(output_path)

    wanted = parse_adc_export(export_path)
    if not wanted:
        raise ValueError('No T&P notice IDs found in export: %s' % export_path)

    log('Export: %s (%d notice IDs)' % (export_path, len(wanted)))
    log('Catalogue: %s' % catalogue_path)

    pub_date, notices = parse_notices(load_tpnms_bytes(catalogue_path))
    wanted_norm = {normalize_notice_id(x) for x in wanted}
    filtered = [n for n in notices if normalize_notice_id(n['id']) in wanted_norm]
    missing = sorted(wanted_norm - {normalize_notice_id(n['id']) for n in filtered})

    if not filtered:
        raise ValueError('Export has %d IDs but none matched catalogue' % len(wanted))

    ts_bytes = datetime.now().strftime('%y-%m-%d %H:%M').encode('ascii') + b'\x00'
    records, stats, has_danger = build_records_for_notices(filtered, ts_bytes, log=log)
    write_aiz_file(records, output_path, has_danger=has_danger, log=log)
    size = os.path.getsize(output_path)
    log('Done: %s (%d bytes)' % (output_path, size))

    return {
        'export': export_path,
        'output': output_path,
        'pub_date': pub_date,
        'wanted': len(wanted_norm),
        'matched': len(filtered),
        'missing': missing,
        'objects': len(records),
        'stats': stats,
        'danger': stats['danger'],
        'size': size,
    }


def build_world_aiz(input_path, output_path, log=None):
    """Собрать worldwide T&P .aiz. Возвращает dict со статистикой."""
    if log is None:
        log = print

    input_path = os.path.abspath(input_path)
    output_path = os.path.abspath(output_path)
    if not os.path.isfile(input_path):
        raise FileNotFoundError('Input not found: %s' % input_path)

    log('Input : %s' % input_path)
    log('Output: %s' % output_path)

    if input_path.lower().endswith('.zip'):
        with zipfile.ZipFile(input_path) as z:
            name = next(n for n in z.namelist() if n.lower().endswith('.xml'))
            xml_bytes = z.read(name)
    else:
        with open(input_path, 'rb') as f:
            xml_bytes = f.read()

    pub_date, notices = parse_notices(xml_bytes)
    n_areas = sum(len(n['areas']) for n in notices)
    n_points = sum(len(n['points']) for n in notices)
    log('Catalogue date: %s' % pub_date)
    log('Parsed %d notices with coordinates: %d areas, %d single points.'
        % (len(notices), n_areas, n_points))

    ts_bytes = datetime.now().strftime('%y-%m-%d %H:%M').encode('ascii') + b'\x00'
    records, stats, has_danger = build_records_for_notices(notices, ts_bytes, log=log)
    log('Constructed %d records (%d areas, %d routes/lines, %d points, %d danger).'
        % (len(records), stats['areas'], stats['lines'], stats['points'], stats['danger']))

    write_aiz_file(records, output_path, has_danger=has_danger, log=log)
    size = os.path.getsize(output_path)
    log('Done: %s (%d bytes)' % (output_path, size))

    return {
        'output': output_path,
        'pub_date': pub_date,
        'notices': len(notices),
        'objects': len(records),
        'areas': stats['areas'],
        'lines': stats['lines'],
        'points': stats['points'],
        'danger': stats['danger'],
        'size': size,
    }


def main():
    ap = argparse.ArgumentParser(description='Generate worldwide T&P .aiz from ADC tpnms data.')
    ap.add_argument('input', nargs='?', help='path to tpnms.zip or tpnms.xml')
    ap.add_argument('-o', '--output', help='output .aiz path (default: "T&P World.aiz" next to script)')
    args = ap.parse_args()

    input_path = args.input
    if not input_path:
        for cand in DEFAULT_INPUTS:
            if os.path.isfile(cand):
                input_path = cand
                break
    if not input_path or not os.path.isfile(input_path):
        sys.exit('Input tpnms.zip/tpnms.xml not found. Pass the path explicitly.')
    input_path = os.path.abspath(input_path)

    output_path = args.output or os.path.join(SCRIPT_DIR, 'T&P World.aiz')
    output_path = os.path.abspath(output_path)

    result = build_world_aiz(input_path, output_path)
    print('================ SUCCESS ================')
    print('File: %s' % result['output'])
    print('Size: %d bytes' % result['size'])
    print('Objects written: %d (%d areas, %d routes/lines, %d points, %d danger)'
          % (result['objects'], result['areas'], result['lines'],
             result['points'], result['danger']))
    print('=========================================')


if __name__ == '__main__':
    main()
