# -*- coding: utf-8 -*-
"""Build Transas .aiz from ADC print/export file (PDF/HTML)."""
import os

from adc_paths import default_output_dir, find_catalogue, route_aiz_path
from generate_world_tpnm_aiz import build_route_aiz


def generate_from_export(export_path, catalogue_path=None, output_path=None):
    catalogue_path = catalogue_path or find_catalogue()
    if not catalogue_path or not os.path.isfile(catalogue_path):
        raise FileNotFoundError('T&P catalogue not found: %s' % catalogue_path)
    if not output_path:
        output_path = route_aiz_path()
    return build_route_aiz(export_path, catalogue_path, output_path)
