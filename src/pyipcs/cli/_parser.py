"""
Subparser registration for the pyIPCS CLI.
"""

from __future__ import annotations

import argparse

from ._commands import (
    handle_create_ddir,
    handle_global_defaults,
    handle_init_dump,
    handle_run,
)
from ._common import add_common_args


def parser_create_ddir(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    """Register the ``create-ddir`` subparser."""
    p = subparsers.add_parser(
        "create-ddir",
        help="Create or open a dump directory (DDIR) by running BLSCDDIR.",
    )
    add_common_args(p)
    p.add_argument(
        "--parms",
        default=None,
        help="Additional parameters to pass to the BLSCDDIR CLIST.",
    )
    p.set_defaults(func=handle_create_ddir)


def parser_global_defaults(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    """Register the ``global-defaults`` subparser."""
    p = subparsers.add_parser(
        "global-defaults",
        help="Set global defaults on an existing DDIR.",
    )
    add_common_args(p)
    p.add_argument(
        "--dump",
        metavar="DSNAME",
        default=None,
        help="Source dump data set name to set as the global default.",
    )
    p.add_argument(
        "--parms",
        default=None,
        help="Additional parameters to pass to the global defaults command.",
    )
    p.set_defaults(func=handle_global_defaults)


def parser_init_dump(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    """Register the ``init-dump`` subparser."""
    p = subparsers.add_parser(
        "init-dump",
        help="Initialize a dump data set in an existing DDIR by running STATUS.",
    )
    add_common_args(p)
    p.add_argument(
        "dump", metavar="DSNAME", help="Source dump data set name to initialize."
    )
    p.set_defaults(func=handle_init_dump)


def parser_run(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    """Register the ``run`` subparser."""
    p = subparsers.add_parser(
        "run",
        help="Run an IPCS subcommand against an existing DDIR.",
    )
    add_common_args(p)
    p.add_argument("subcmd", help="IPCS subcommand to run.")
    p.add_argument(
        "--dump",
        metavar="DSNAME",
        default=None,
        help="Source dump data set name for this invocation.",
    )
    p.add_argument(
        "--auth",
        action="store_true",
        default=False,
        help="Run the subcommand in an authorized environment.",
    )
    p.add_argument(
        "--local-defaults",
        default=None,
        help="Parameters for SETDEF NOLIST LOCAL run before the subcommand.",
    )
    p.set_defaults(func=handle_run)
