#!/usr/bin/env python3
"""Launcher used by .mcp.json: works from any working directory, no install step."""
import os
import runpy
import sys

if sys.version_info < (3, 9):
    sys.stderr.write("SEODevil needs Python 3.9 or newer.\n")
    sys.exit(1)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
runpy.run_module("seodevil_mcp", run_name="__main__")
