#!/usr/bin/env python

import sys
import pyconcrete
import logging
from src.migrate import cli

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sys.exit(cli())
