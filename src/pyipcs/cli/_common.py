"""
Shared argument helpers for the pyIPCS CLI.
"""

from __future__ import annotations

import argparse
import json


def load_allocations(path: str | None) -> dict[str, str | list[str]] | None:
    """Load allocations from a JSON file, or return ``None`` to use defaults.

    The JSON file must contain an object whose keys are DD names and values are
    string data set allocation requests or lists of cataloged dataset names::

        {
            "IPCSPARM": "SYS1.PARMLIB",
            "SYSPROC": ["SYS1.SBLSCLI0", "MY.SBLSCLI0"]
        }

    Args:
        path: Path to the JSON file, or ``None`` to use defaults.

    Returns:
        dict[str, str | list[str]] | None: Allocations dictionary, or ``None``
        if ``path`` is ``None``.

    Raises:
        argparse.ArgumentTypeError: If the file cannot be read or is not valid.
    """
    if path is None:
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def add_common_args(parser: argparse.ArgumentParser) -> None:
    """Add the shared ``dsname`` positional arg and ``--driver`` / ``--allocations`` flags.

    Args:
        parser: The subparser to add arguments to.
    """
    parser.add_argument("ddir", help="Data set name of the DDIR.")
    parser.add_argument(
        "--driver",
        metavar="DSNAME",
        default=None,
        help="Driver data set name to use for the DDIR.",
    )
    parser.add_argument(
        "--allocations",
        metavar="FILE",
        default=None,
        help=(
            "Path to a JSON file containing custom TSO/E allocations. "
            "The file must be a JSON object where keys are DD names and values "
            "are string allocation requests or lists of dataset names. "
            'Defaults to {"IPCSPARM": "SYS1.PARMLIB", "SYSPROC": "SYS1.SBLSCLI0"}.'
        ),
    )
