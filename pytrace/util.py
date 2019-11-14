# -*- coding: utf-8 -*-

import sys

colors = {
    "red": 31,
    "green": 32,
    "yellow": 33,
    "blue": 34,
}


def colored(text, color="green"):
    if sys.stdout.isatty():
        return "\033[{}m{}\033[0m".format(colors[color], text)
    else:
        return text
