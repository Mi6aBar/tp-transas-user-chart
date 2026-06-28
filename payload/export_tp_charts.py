# -*- coding: utf-8 -*-
"""Export T&P notices to Furuno XML, JRC CSV and JRC UCH (hidden)."""
import os
import re
import struct
import time
import xml.sax.saxutils as xml_escape

from generate_world_tpnm_aiz import classify_record_danger, is_route, notice_combined_text

FURUNO_MAX_POINTS = 200
FURUNO_BETA2_MAX_POINTS = 200
FURUNO_PROFILE_ROUTE = 'route'
FURUNO_PROFILE_BETA2 = 'beta2'
FURUNO_MAX_NAME_LEN = 52
FURUNO_CIRCLE_RANGE_NM = 0.5
FURUNO_DANGER_RE = re.compile(
    r'(?i)\b(mine|mines|drill|drilling|firing|missile|rocket|gunnery|'
    r'explosive|hazard|weapon|detonation)\b'
)

# JRC UCH — kept for future use (not exposed in UI).
JRC_UCH_SCALE = 6000000
JRC_UCH_CONST = 100000000
JRC_UCH_CONST2 = 1000
JRC_UCH_HEADER_SIZE = 144
JRC_UCH_LABEL_SIZE = 64
JRC_UCH_TYPE_POINT = 1
JRC_UCH_TYPE_NOTICE_POINT = 7
JRC_UCH_TYPE_LINE = 3
JRC_UCH_TYPE_USER_POLY = 6
JRC_UCH_TYPE_ROUTE_POLY = 10
JRC_UCH_POINT_SIZE = 96
JRC_UCH_NOTICE_POINT_SIZE = 108
JRC_UCH_POINT_TAIL = b'~CIRCLE0\x00\x00\x00\x00'
JRC_UCH_NOTICE_POINT_META = bytes.fromhex('0104040003020000')
JRC_UCH_NOTICE_POINT_RADIUS = 5
JRC_UCH_USER_POLY_META = bytes.fromhex('0104040003070000')
JRC_UCH_ROUTE_POLY_META = bytes.fromhex('01040000030000000000')
JRC_UCH_LINE_META = bytes.fromhex('010404000000')
JRC_UCH_MAX_VERTS = 400
JRC_UCH_MAX_LABEL_LEN = 63


def decimal_to_jrc(lat, lon):
    lat_d = int(abs(lat))
    lat_m = (abs(lat) - lat_d) * 60
    lat_h = 'N' if lat >= 0 else 'S'
    lon_d = int(abs(lon))
    lon_m = (abs(lon) - lon_d) * 60
    lon_h = 'E' if lon >= 0 else 'W'
    return str(lat_d), f'{lat_m:.3f}', lat_h, f'{lon_d},{lon_m:.3f},{lon_h}'


def _jrc_text_lines(name, lat, lon):
    lat_d, lat_m, lat_h, lon_part = decimal_to_jrc(lat, lon)
    return [
        '// TEXT', '// Comment', '// Lat,,,Lon,Rotation',
        'TEXT,%s' % name,
        name,
        '%s,%s,%s,%s,0,18,' % (lat_d, lat_m, lat_h, lon_part),
    ]


def normalize_lon(lon):
    while lon > 180.0:
        lon -= 360.0
    while lon < -180.0:
        lon += 360.0
    return lon


def normalize_coord(lat, lon):
    return max(-90.0, min(90.0, float(lat))), normalize_lon(float(lon))


def polygon_centroid(coords):
    if not coords:
        return 0.0, 0.0
    return (
        sum(c[0] for c in coords) / len(coords),
        sum(c[1] for c in coords) / len(coords),
    )


def close_ring(coords):
    if not coords:
        return []
    ring = [normalize_coord(lat, lon) for lat, lon in coords]
    if ring[0] != ring[-1]:
        ring.append(ring[0])
    return ring


def polygon_label_centroid_for_area(coords, open_ring=False):
    """Label position for polygon areas (Route TP closed XML, NAVAREA open XML)."""
    if not coords:
        return 0.0, 0.0
    if open_ring:
        ring = close_ring(coords)
    else:
        ring = close_ring(coords)
    return polygon_centroid(ring)


def furuno_profile_for_chart_format(chart_format):
    if chart_format == 'furuno_beta2':
        return FURUNO_PROFILE_BETA2
    if chart_format == 'furuno':
        return FURUNO_PROFILE_ROUTE
    return None


def furuno_max_points(profile):
    if profile == FURUNO_PROFILE_BETA2:
        return FURUNO_BETA2_MAX_POINTS
    return FURUNO_MAX_POINTS


def furuno_area_vertices(coords):
    verts = [normalize_coord(lat, lon) for lat, lon in coords]
    if len(verts) >= 2 and verts[0] == verts[-1]:
        verts = verts[:-1]
    return verts


def furuno_area_ring(coords):
    return close_ring(furuno_area_vertices(coords))


def furuno_line_coords(coords):
    return [normalize_coord(lat, lon) for lat, lon in coords]


def furuno_check_danger(notice, kind):
    is_poly = kind == 'polygon'
    is_rt = kind == 'line'
    if classify_record_danger(notice, is_poly=is_poly, is_route=is_rt):
        return '1'
    if FURUNO_DANGER_RE.search(notice_combined_text(notice)):
        return '1'
    return '0'


def furuno_object_description(display_name, notice):
    title = re.sub(r'\s+', ' ', (notice.get('title') or '').strip().split('\n')[0])
    if len(title) > 36:
        title = title[:36].rsplit(' ', 1)[0]
    if title:
        return '%s - %s' % (display_name, title)
    return display_name


def furuno_display_name(label):
    """2474(T)/26 Area 2/4 -> 2474-T-26 Area 2-4 (Route TP sample format)."""
    s = (label or '').strip()
    m = re.match(r'^(\d+)\(([TP])\)/(\d+)(.*)$', s)
    if m:
        s = '%s-%s-%s%s' % (m.group(1), m.group(2), m.group(3), m.group(4))
    s = re.sub(r' Area (\d+)/(\d+)', r' Area \1-\2', s)
    s = re.sub(r' Pt (\d+)/(\d+)', r' Pt \1-\2', s)
    s = re.sub(r' Line (\d+)/(\d+)', r' Line \1-\2', s)
    return s


def furuno_safe_name(name, used, index):
    s = furuno_display_name(name)
    s = re.sub(r'[^\w \-./]', '-', s)
    s = re.sub(r'-+', '-', s)
    s = re.sub(r'\s+', ' ', s).strip().strip('-')
    if len(s) > FURUNO_MAX_NAME_LEN:
        s = s[:FURUNO_MAX_NAME_LEN]
    if not s:
        s = 'obj-%d' % index
    return s


def furuno_safe_chart_name(name):
    s = (name or 'User Chart').replace('&', ' and ')
    s = re.sub(r'[^\w \-./]', '-', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s[:FURUNO_MAX_NAME_LEN] or 'User Chart'


def iter_tp_features(notices):
    for n in notices:
        nid = n['id']
        route = is_route(n['title'], n['body'])
        total_areas = len(n['areas'])
        total_pts = len(n['points'])
        multi = (total_areas + total_pts) > 1

        for ai, run in enumerate(n['areas'], 1):
            coords = [normalize_coord(lat, lon) for lat, lon, _ in run]
            if route:
                kind = 'line'
                suffix = ' Line %d/%d' % (ai, total_areas) if multi else ''
            else:
                kind = 'polygon'
                suffix = ' Area %d/%d' % (ai, total_areas) if multi else ''
            yield {
                'kind': kind,
                'label': nid + suffix,
                'coords': coords,
                'notice': n,
            }

        for pi, (lat, lon, _disp) in enumerate(n['points'], 1):
            suffix = ' Pt %d/%d' % (pi, total_pts) if multi else ''
            yield {
                'kind': 'point',
                'label': nid + suffix,
                'coords': [normalize_coord(lat, lon)],
                'notice': n,
            }


def feature_point_cost(feat, profile=FURUNO_PROFILE_ROUTE):
    kind = feat['kind']
    coords = feat['coords']
    if profile == FURUNO_PROFILE_BETA2:
        if kind == 'polygon' and len(coords) >= 3:
            return len(furuno_area_vertices(coords)) + 1
        if kind == 'line':
            line = furuno_line_coords(coords)
            if len(line) >= 2:
                return len(line) + 1
            if len(line) == 1:
                return 1
            return 0
        if kind == 'point':
            return len(coords) or 1
        return 0

    if kind == 'polygon' and len(coords) >= 3:
        return len(close_ring(coords)) + 1
    if kind == 'line':
        line = furuno_line_coords(coords)
        if len(line) >= 2:
            return len(line)
        if len(line) == 1:
            return 1
        return 0
    if kind == 'point':
        return len(coords) or 1
    return 0


def estimate_furuno_points(notices, profile=FURUNO_PROFILE_ROUTE):
    return sum(feature_point_cost(f, profile=profile) for f in iter_tp_features(notices))


def build_jrc_csv(chart_name, notices, chart_subtitle=''):
    lines = [
        '// USER CHART SHEET exported by JRC ECDIS.',
        '// <<NOTE>>This strings // indicate comment column/cells. You can edit freely.',
        '// %s,,' % chart_name,
        '// DANGER_SYMBOL,InstName', '// Comment', '// Lat,,,Lon',
    ]
    for feat in iter_tp_features(notices):
        name = feat['label']
        kind = feat['kind']
        coords = feat['coords']

        if kind == 'polygon' and len(coords) >= 3:
            ring = close_ring(coords)
            lines += [
                '// DANGER_AREA', '// Comment',
                '// Lat,,,Lon,Add "END" to the end of vertex.',
                'DANGER_AREA', name,
            ]
            for lat, lon in ring:
                lat_d, lat_m, lat_h, lon_part = decimal_to_jrc(lat, lon)
                lines.append('%s,%s,%s,%s' % (lat_d, lat_m, lat_h, lon_part))
            lines.append('END')
            cen = polygon_centroid(ring)
            lines += _jrc_text_lines(name, cen[0], cen[1])
        elif kind == 'line' and len(coords) >= 2:
            lines += [
                '// LINE_AGGREGATE', '// Comment',
                '// Lat,,,Lon,,,Type,Width,ColorNo,Comment',
                '// Add "END" to the end of vertex.',
                'LINE_AGGREGATE', name,
            ]
            for lat, lon in coords:
                lat_d, lat_m, lat_h, lon_part = decimal_to_jrc(lat, lon)
                lines.append('%s,%s,%s,%s,2,4,9,%s' % (lat_d, lat_m, lat_h, lon_part, name))
            lines.append('END')
            cen = polygon_centroid(coords)
            lines += _jrc_text_lines(name, cen[0], cen[1])
        elif kind == 'point' or (kind == 'line' and len(coords) == 1):
            for lat, lon in coords:
                lat_d, lat_m, lat_h, lon_part = decimal_to_jrc(lat, lon)
                lines += [
                    '// DANGER_SYMBOL,InstName', '// Comment', '// Lat,,,Lon',
                    'DANGER_SYMBOL,~WARNSY0,***,***', name,
                    '%s,%s,%s,%s' % (lat_d, lat_m, lat_h, lon_part),
                ]
    return '\r\n'.join(lines) + '\r\n'


def jrc_uch_safe_label(name):
    s = re.sub(r'\s+', ' ', (name or '').strip())
    if len(s) > JRC_UCH_MAX_LABEL_LEN:
        s = s[:JRC_UCH_MAX_LABEL_LEN]
    return s


def jrc_uch_coord_i(lat, lon):
    lat, lon = normalize_coord(lat, lon)
    return (
        int(round(lat * JRC_UCH_SCALE)),
        int(round(lon * JRC_UCH_SCALE)),
    )


def jrc_uch_coord_bytes(lat, lon):
    lat_i, lon_i = jrc_uch_coord_i(lat, lon)
    return struct.pack('<ii', lat_i, lon_i)


def jrc_uch_label_block(label):
    raw = jrc_uch_safe_label(label).encode('ascii', 'replace')
    raw = raw[:JRC_UCH_LABEL_SIZE - 1]
    return raw + (b'\x00' * (JRC_UCH_LABEL_SIZE - len(raw)))


def jrc_uch_record_header(rec_type, label):
    return (
        struct.pack('<III', rec_type, JRC_UCH_CONST, JRC_UCH_CONST2)
        + jrc_uch_label_block(label)
    )


def jrc_uch_notice_point_record(label, lat, lon, radius=JRC_UCH_NOTICE_POINT_RADIUS):
    lat_i, lon_i = jrc_uch_coord_i(lat, lon)
    body = (
        jrc_uch_record_header(JRC_UCH_TYPE_NOTICE_POINT, label)
        + JRC_UCH_NOTICE_POINT_META
        + struct.pack('<II', radius, radius)
        + struct.pack('<i', lat_i)
        + struct.pack('<ii', lon_i, lat_i)
        + b'\x00\x00\x00\x00'
    )
    if len(body) != JRC_UCH_NOTICE_POINT_SIZE:
        raise ValueError('JRC UCH notice point size %d != %d' % (len(body), JRC_UCH_NOTICE_POINT_SIZE))
    return body


def jrc_uch_route_poly_meta(n_verts):
    return JRC_UCH_ROUTE_POLY_META + struct.pack('<H', n_verts)


def jrc_uch_line_meta(n_verts):
    return JRC_UCH_LINE_META + struct.pack('<H', n_verts)


def jrc_uch_area_chunks(coords, close=True):
    if close:
        ring = close_ring(coords)
    else:
        ring = [normalize_coord(lat, lon) for lat, lon in coords]
    if len(ring) <= JRC_UCH_MAX_VERTS:
        return [ring]
    verts = ring[:]
    if close and len(verts) >= 2 and verts[0] == verts[-1]:
        verts = verts[:-1]
    chunks = []
    step = JRC_UCH_MAX_VERTS - 1
    i = 0
    while i < len(verts):
        remain = len(verts) - i
        if remain <= JRC_UCH_MAX_VERTS - 1:
            chunk = verts[i:] + ([verts[0]] if close else [])
        else:
            chunk = verts[i:i + step] + ([verts[i]] if close else [])
        chunks.append(chunk)
        if remain <= JRC_UCH_MAX_VERTS - 1:
            break
        i += step - 1 if close else step
    return chunks


def jrc_uch_poly_record(label, verts):
    parts = [
        jrc_uch_record_header(JRC_UCH_TYPE_ROUTE_POLY, label),
        jrc_uch_route_poly_meta(len(verts)),
    ]
    for lat, lon in verts:
        parts.append(jrc_uch_coord_bytes(lat, lon))
    return b''.join(parts)


def jrc_uch_line_record(label, verts):
    parts = [
        jrc_uch_record_header(JRC_UCH_TYPE_LINE, label),
        jrc_uch_line_meta(len(verts)),
    ]
    for lat, lon in verts:
        parts.append(jrc_uch_coord_bytes(lat, lon))
    return b''.join(parts)


def build_jrc_uch(chart_name, notices):
    body = bytearray()
    for feat in iter_tp_features(notices):
        label = jrc_uch_safe_label(feat['label'])
        kind = feat['kind']
        coords = feat['coords']
        if kind == 'polygon' and len(coords) >= 3:
            for chunk in jrc_uch_area_chunks(coords, close=True):
                body += jrc_uch_poly_record(label, chunk)
        elif kind == 'line' and len(coords) >= 2:
            for chunk in jrc_uch_area_chunks(coords, close=False):
                body += jrc_uch_line_record(label, chunk)
        elif kind == 'point' or (kind == 'line' and len(coords) == 1):
            for lat, lon in coords:
                body += jrc_uch_notice_point_record(label, lat, lon)

    header = bytearray(JRC_UCH_HEADER_SIZE)
    title = (jrc_uch_safe_label(chart_name) or 'TP Chart').encode('ascii', 'replace')[:127]
    header[16:16 + len(title)] = title
    data = bytes(header) + bytes(body)
    patched = bytearray(data)
    struct.pack_into('<II', patched, 0, len(patched), int(time.time()))
    return bytes(patched)


def write_jrc_uch_file(notices, output_path, chart_name='TP World', chart_subtitle='', log=None):
    if log:
        log('Writing JRC JAN-701B UCH…')
    name = chart_name
    if chart_subtitle and chart_subtitle not in chart_name:
        name = '%s %s' % (chart_name, chart_subtitle)
    data = build_jrc_uch(name, notices)
    os.makedirs(os.path.dirname(os.path.abspath(output_path)) or '.', exist_ok=True)
    with open(output_path, 'wb') as f:
        f.write(data)
    return len(data)


def _furuno_verts_xml(coords):
    return '\n'.join(
        '        <vertex id="%d" latitude="%.6f" longitude="%.6f"/>'
        % (i, lat, lon)
        for i, (lat, lon) in enumerate(coords, start=1)
    )


def _furuno_area_xml(safe_name, coords, check_danger='0'):
    return (
        '    <area name="%s" description="">\n'
        '      <position>\n%s\n      </position>\n'
        '      <type checkDanger="%s" displayRadar="0" hasNotes="0" notesType="0"/>\n'
        '    </area>' % (safe_name, _furuno_verts_xml(coords), check_danger)
    )


def _furuno_line_xml(safe_name, coords, check_danger='1'):
    return (
        '    <line name="%s" description="">\n'
        '      <position>\n%s\n      </position>\n'
        '      <attribute lineType="2"/>\n'
        '      <type checkDanger="%s" displayRadar="0" hasNotes="0" rangeOfNotes="1.000000"/>\n'
        '    </line>' % (safe_name, _furuno_verts_xml(coords), check_danger)
    )


def _furuno_label_xml(safe_name, lat, lon):
    return (
        '    <label name="%s" description="%s">\n'
        '      <position>\n'
        '        <vertex id="1" latitude="%.6f" longitude="%.6f"/>\n'
        '      </position>\n'
        '      <attribute labelStyle="2" labelText="%s"/>\n'
        '      <type checkDanger="0" displayRadar="0"/>\n'
        '    </label>' % (safe_name, safe_name, lat, lon, safe_name)
    )


def _furuno_xml_body(chart_name, lines_xml, areas_xml, labels_xml, profile=FURUNO_PROFILE_ROUTE):
    blocks = [
        '<?xml version="1.0" encoding="UTF-8"?>\n',
        '<!--userchart node-->\n',
        '<userchart name="%s" description="" version="1.0">\n' % xml_escape.escape(chart_name),
    ]
    if lines_xml:
        blocks.append('  <!--userchart line-->\n')
        blocks.append('  <lines>\n' + '\n'.join(lines_xml) + '\n  </lines>\n')
    if areas_xml:
        if profile == FURUNO_PROFILE_BETA2:
            blocks.append('  <!--userchart area-->\n')
        blocks.append('  <areas>\n' + '\n'.join(areas_xml) + '\n  </areas>\n')
    if labels_xml:
        if profile == FURUNO_PROFILE_BETA2:
            blocks.append('  <!--userchart label-->\n')
        blocks.append('  <labels>\n' + '\n'.join(labels_xml) + '\n  </labels>\n')
    blocks.append('</userchart>\n')
    return ''.join(blocks)


def build_furuno_xml_from_features(chart_name, features, used_names=None, chart_description='',
                                   profile=FURUNO_PROFILE_ROUTE):
    """Furuno userchart XML (Route TP or NAVAREA-style BETA2)."""
    lines_xml, areas_xml, labels_xml = [], [], []
    idx = 0
    chart_name = furuno_safe_chart_name(chart_name)
    points = 0

    for feat in features:
        idx += 1
        display = furuno_safe_name(feat['label'], None, idx)
        safe_name = xml_escape.escape(display)
        kind = feat['kind']
        coords = feat['coords']
        notice = feat.get('notice')
        check_danger = furuno_check_danger(notice, kind) if notice else '0'

        if kind == 'polygon' and len(coords) >= 3:
            if profile == FURUNO_PROFILE_BETA2:
                ring = furuno_area_vertices(coords)
                points += len(ring)
                areas_xml.append(_furuno_area_xml(safe_name, ring, check_danger=check_danger))
                cen = polygon_label_centroid_for_area(coords, open_ring=True)
            else:
                ring = close_ring(coords)
                points += len(ring)
                areas_xml.append(_furuno_area_xml(safe_name, ring, check_danger='0'))
                cen = polygon_centroid(ring)
            labels_xml.append(_furuno_label_xml(safe_name, cen[0], cen[1]))
            points += 1
        elif kind == 'line':
            line = furuno_line_coords(coords)
            if len(line) >= 2:
                if profile == FURUNO_PROFILE_BETA2:
                    lines_xml.append(_furuno_line_xml(safe_name, line, check_danger=check_danger))
                    points += len(line)
                    cen = polygon_centroid(line)
                    labels_xml.append(_furuno_label_xml(safe_name, cen[0], cen[1]))
                    points += 1
                else:
                    for lat, lon in line:
                        labels_xml.append(_furuno_label_xml(safe_name, lat, lon))
                        points += 1
            elif len(line) == 1:
                lat, lon = line[0]
                labels_xml.append(_furuno_label_xml(safe_name, lat, lon))
                points += 1
        elif kind == 'point':
            for lat, lon in coords:
                labels_xml.append(_furuno_label_xml(safe_name, lat, lon))
                points += 1

    body = _furuno_xml_body(chart_name, lines_xml, areas_xml, labels_xml, profile=profile)
    return body, {
        'furuno_points': points,
        'furuno_lines': len(lines_xml),
        'furuno_areas': len(areas_xml),
        'furuno_circles': 0,
        'furuno_labels': len(labels_xml),
    }


def pack_furuno_features(features, max_points=FURUNO_MAX_POINTS, profile=FURUNO_PROFILE_ROUTE):
    packs = []
    current = []
    current_pts = 0
    skipped = []
    for feat in features:
        cost = feature_point_cost(feat, profile=profile)
        if cost <= 0:
            continue
        if cost > max_points:
            skipped.append(feat)
            continue
        if current and current_pts + cost > max_points:
            packs.append(current)
            current = []
            current_pts = 0
        current.append(feat)
        current_pts += cost
    if current:
        packs.append(current)
    return packs, skipped


def build_furuno_xml(chart_name, notices, profile=FURUNO_PROFILE_ROUTE):
    features = list(iter_tp_features(notices))
    text, part_meta = build_furuno_xml_from_features(
        furuno_safe_chart_name(chart_name), features, profile=profile)
    point_count = estimate_furuno_points(notices, profile=profile)
    point_limit = furuno_max_points(profile)
    return text, {
        'furuno_points': part_meta['furuno_points'],
        'furuno_limit': point_limit,
        'furuno_over_limit': point_count > point_limit,
        'furuno_areas': part_meta['furuno_areas'],
        'furuno_labels': part_meta['furuno_labels'],
        'furuno_lines': part_meta['furuno_lines'],
        'furuno_files': 1,
    }


def _furuno_cleanup_old_xml(output_dir, chart_name):
    prefix = furuno_safe_chart_name(chart_name).lower()
    for name in os.listdir(output_dir):
        low = name.lower()
        if low.endswith('.xml') and low.startswith(prefix):
            try:
                os.remove(os.path.join(output_dir, name))
            except OSError:
                pass


def write_furuno_files(notices, output_dir, chart_name='TP World', log=None,
                       profile=FURUNO_PROFILE_ROUTE):
    point_limit = furuno_max_points(profile)
    if log:
        log('Writing Furuno XML (split by %d point limit)…' % point_limit)

    features = list(iter_tp_features(notices))
    packs, skipped = pack_furuno_features(features, max_points=point_limit, profile=profile)
    if not packs:
        raise ValueError('No Furuno features to export')

    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    _furuno_cleanup_old_xml(output_dir, chart_name)

    base_name = furuno_safe_chart_name(chart_name)
    files = []
    total_bytes = 0
    total_points = 0
    n_parts = len(packs)

    for i, pack in enumerate(packs, 1):
        part_title = '%s %02d' % (base_name, i) if n_parts > 1 else base_name
        fname = '%s %02d.xml' % (base_name, i) if n_parts > 1 else '%s.xml' % base_name
        fpath = os.path.join(output_dir, fname)
        text, part_meta = build_furuno_xml_from_features(
            part_title, pack, profile=profile)
        data = text.encode('utf-8')
        with open(fpath, 'wb') as f:
            f.write(data)
        files.append(fpath)
        total_bytes += len(data)
        total_points += part_meta['furuno_points']
        if log:
            log('  part %d/%d: %s (%d points)' % (
                i, n_parts, fname, part_meta['furuno_points']))

    if log:
        log('Furuno: %d file(s), %d points total' % (len(files), total_points))
        if skipped:
            log('WARNING: %d object(s) skipped (exceed %d points each)' % (
                len(skipped), point_limit))

    meta = {
        'furuno_points': total_points,
        'furuno_limit': point_limit,
        'furuno_files': len(files),
        'furuno_skipped': len(skipped),
        'furuno_output_dir': output_dir,
        'output': output_dir,
    }
    return total_bytes, meta


def write_furuno_file(notices, output_path, chart_name='TP World', log=None,
                      profile=FURUNO_PROFILE_ROUTE):
    if os.path.splitext(output_path)[1].lower() == '.xml':
        output_dir = os.path.dirname(output_path)
    else:
        output_dir = output_path
    return write_furuno_files(
        notices, output_dir, chart_name=chart_name, log=log, profile=profile)


def count_export_objects(notices):
    return sum(1 for _ in iter_tp_features(notices))


def write_jrc_file(notices, output_path, chart_name='TP World', chart_subtitle='', log=None):
    if log:
        log('Writing JRC CSV…')
    text = build_jrc_csv(chart_name, notices, chart_subtitle=chart_subtitle)
    os.makedirs(os.path.dirname(os.path.abspath(output_path)) or '.', exist_ok=True)
    with open(output_path, 'wb') as f:
        f.write(text.encode('utf-8'))
    return len(text.encode('utf-8'))
