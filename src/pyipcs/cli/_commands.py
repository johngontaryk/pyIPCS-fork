"""
Command handler functions for the pyIPCS CLI.
"""

from __future__ import annotations

import argparse
import sys

from ..dump import IpcsDump
from ..ddir import IpcsDdir
from ._common import load_allocations


def handle_create_ddir(args: argparse.Namespace) -> None:
    """Handle the ``create-ddir`` command."""
    ddir = IpcsDdir(
        args.ddir,
        driver=args.driver,
        allocations=load_allocations(args.allocations),
        parms=args.parms,
    )
    print(ddir.response.output, end="")
    sys.exit(ddir.response.rc)


def handle_global_defaults(args: argparse.Namespace) -> None:
    """Handle the ``global-defaults`` command."""
    ddir = IpcsDdir(
        args.ddir,
        driver=args.driver,
        allocations=load_allocations(args.allocations),
    )
    response = ddir.set_global_defaults(
        dump=IpcsDump(args.dump) if args.dump else None,
        parms=args.parms,
    )
    print(response.output, end="")
    sys.exit(response.rc)


def handle_init_dump(args: argparse.Namespace) -> None:
    """Handle the ``init-dump`` command."""
    dump = IpcsDump(args.dump)
    ddir = IpcsDdir(
        args.ddir,
        driver=args.driver,
        allocations=load_allocations(args.allocations),
    )
    response = ddir.init_dump(dump)
    if response.rc >= 8:
        print(
            "Dump initialization unsuccessful: "
            "Error encountered while running the 'STATUS' subcommand to initialize dump."
        )
        sys.exit(response.rc)
    if dump.dsname not in ddir.sources():
        print(
            "Dump initialization unsuccessful: "
            "Dump not listed as a source description."
        )
        sys.exit(1)
    print("Dump initialization successful.")
    sys.exit(0)


def handle_run(args: argparse.Namespace) -> None:
    """Handle the ``run`` command."""
    ddir = IpcsDdir(
        args.ddir,
        driver=args.driver,
        allocations=load_allocations(args.allocations),
    )
    response = ddir.run(
        args.subcmd,
        dump=IpcsDump(args.dump) if args.dump else None,
        authorized=args.auth,
        local_defaults=args.local_defaults,
        output=sys.stdout,
    )
    sys.exit(response.rc)
