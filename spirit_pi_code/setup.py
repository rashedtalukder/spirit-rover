"""
Compatibility shim for legacy tooling.

All project metadata now lives in ``pyproject.toml``. This file remains only so
that ``pip install -e .`` keeps working on older pip/setuptools versions.
"""

from setuptools import setup

setup()
