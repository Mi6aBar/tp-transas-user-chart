# -*- coding: utf-8 -*-
"""Build user chart from ADC print/export file (PDF/HTML)."""
import os

from adc_paths import find_catalogue, route_output_path
from generate_world_tpnm_aiz import build_route_chart


def generate_from_export(export_path, catalogue_path=None, output_path=None):
    catalogue_path = catalogue_path or find_catalogue()
    if not catalogue_path or not os.path.isfile(catalogue_path):
        raise FileNotFoundError('T&P catalogue not found: %s' % catalogue_path)
    if not output_path:
        output_path = route_output_path()
    return build_route_chart(export_path, catalogue_path, output_path)
