#!/usr/bin/env python

import sys
import pyconcrete
import logging
from src.irrcache import cli

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sys.exit(cli())
