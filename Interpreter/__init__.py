"""Interpreter is an easy way to interpret code at high resolution and with understandable semantics."""

from sys import version_info
from warnings import warn
if version_info < (3, 10):
    warn("Warning: Interpreter is instable at a version lesser than 3.10 of python.")

__author__ = (
    "Neo Zetterberg", 
)