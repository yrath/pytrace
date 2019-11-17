# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(
    name="pytrace",
    version="0.0.1",
    packages=find_packages(exclude=["img"]),
    author="Yannik Rath",
    description="Trace python program execution at runtime.",
    scripts=["bin/pytrace"],
    install_requires=["pygments"],
)
