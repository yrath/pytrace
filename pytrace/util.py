# -*- coding: utf-8 -*-

colors = {
    "red": 31,
    "green": 32,
    "yellow": 33,
    "blue": 34,
}


def colored(text, color="green"):
    return "\033[{}m{}\033[0m".format(colors[color], text)
