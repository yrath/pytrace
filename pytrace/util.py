# -*- coding: utf-8 -*-

import sys

from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import TerminalFormatter

colors = {
    "red": 31,
    "green": 32,
    "yellow": 33,
    "blue": 34,
}

lexer = PythonLexer()
formatter = TerminalFormatter()


def colored(text, color="green"):
    if sys.stdout.isatty():
        return "\033[{}m{}\033[0m".format(colors[color], text)
    else:
        return text


def highlight_code(text):
    if sys.stdout.isatty():
        return highlight(text, lexer, formatter)
    else:
        return text


def only_simple_types(obj):
    if isinstance(obj, (int, float, str, bool)):
        return True
    elif isinstance(obj, (list, tuple)):
        return all([only_simple_types(elem) for elem in obj])
    return False
