# pylint: disable=wrong-import-position
"""
pyIPCS Exports
"""

import sys

if sys.platform != "zos":
    raise RuntimeError("This package is only supported on z/OS.")

from ._version import __version__
from . import util
from . import exceptions
from .allocation import IpcsAllocation
from .dump import IpcsDump
from .session import IpcsSession
