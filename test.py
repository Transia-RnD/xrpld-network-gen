#!/usr/bin/env python
# coding: utf-8

import os
import shutil
import sys

import pytest

from basedir import basedir


def main():
    """main.py."""
    argv = []

    argv.extend(sys.argv[1:])

    pytest.main(argv)

    try:
        os.remove(os.path.join(basedir, ".coverage"))

    except OSError:
        pass

    try:
        shutil.rmtree(os.path.join(basedir, ".cache"))

    except OSError:
        pass

    try:
        shutil.rmtree(os.path.join(basedir, "tests/.cache"))
    except OSError:
        pass


if __name__ == "__main__":
    main()
