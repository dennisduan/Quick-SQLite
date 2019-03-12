"""
SQL Wrapper
~~~~~~~~~~~

A simple SQLite3 wrapper built for
beginners of SQL.
"""

from .connect import Connection
from collections import namedtuple

import logging

VersionInfo = namedtuple('VersionInfo', 'major minor micro releaselevel serial')

version_info = VersionInfo(major=1, minor=0, micro=2, releaselevel='stable', serial=0)

try:
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass

logging.getLogger(__name__).addHandler(NullHandler())