"""
pyIPCS command-line interface entry point.
"""

from __future__ import annotations

import argparse
import sys
import os
from .allocation import IpcsAllocation
from .dump import IpcsDump
from .ddir import IpcsDdir
from .exceptions import TsoError

def _parse_allocations() -> list[IpcsAllocation] | None:
    """Parse IPCS allocations from environment variables.

    Set the ``IPCSALLOC`` environment variable to provide custom allocations as
    a colon-separated list of DD names, then set each DD name as its own
    environment variable — identical to how tsocmd uses ``TSOALLOC``:

    ```
    export IPCSALLOC=IPCSPARM:SYSPROC
    export IPCSPARM=MY.PARMLIB
    export SYSPROC=MY.SBLSCLI0
    ```

    Each DD variable value is passed through as-is to the TSO shell script, so
    both dataset-name strings and allocation strings are supported:

    ```
    export ISPPROF="ALLOC NEW UNIT(SYSVIO) SPACE(1,1) CYL DIR(5) RECFM(F,B) LRECL(80) BLKSIZE(3120)"
    export ISPPLIB=SYS1.SBPXPENU:SYS1.ISP.SISPPENU
    ```

    If ``IPCSALLOC`` is not set, the default allocations are
    dataset ``SYS1.PARMLIB`` for DD name ``IPCSPARM``
    and dataset ``SYS1.SBLSCLI0`` for DD name ``SYSPROC``.

    Returns:
        list[IpcsAllocation] or None: Allocations or ``None`` to use default IPCS allocations.
    """
    env_map = os.environ
    ipcsalloc = env_map.get("IPCSALLOC")
    if ipcsalloc is None:
        return None

    dd_names = [dd_name.strip() for dd_name in ipcsalloc.strip().split(":")]

    if any(not dd_name for dd_name in dd_names):
        raise TsoError("IPCSALLOC contains empty DD names.")
    if len(dd_names) != len(set(dd_names)):
        raise TsoError("IPCSALLOC contains duplicate DD names.")

    allocations: list[IpcsAllocation] = []
    for dd_name in dd_names:
        spec = env_map.get(dd_name)
        if spec is None:
            raise TsoError(f"Specification for DD name {dd_name} does not exist.")
        if not spec:
            raise TsoError(f"Specification for DD name {dd_name} is empty.")

        allocations.append(IpcsAllocation(dd_name=dd_name, specification=spec))

    return allocations

# ---------------------------------------------------------------------------
# create-ddir command
# ---------------------------------------------------------------------------

def _cmd_create_ddir(args: argparse.Namespace) -> int:
    """Run the ``create-ddir`` CLI command."""
    ddir = IpcsDdir(
        args.dsname,
        driver=args.driver,
        allocations=_parse_allocations(),
        parms=args.parms,
    )
    print(ddir.response.output, end="")
    sys.exit(ddir.response.rc)


def _add_create_ddir_parser(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    """Add the ``create-ddir`` subparser."""
    create_ddir_parser = subparsers.add_parser(
        "create-ddir",
        help="Create or open a dump directory (DDIR) by running BLSCDDIR.",
    )
    create_ddir_parser.add_argument("dsname", help="Data set name of the DDIR.")
    create_ddir_parser.add_argument(
        "--driver",
        metavar="DSNAME",
        default=None,
        help="Driver data set name to use for the DDIR.",
    )
    create_ddir_parser.add_argument(
        "--parms",
        default=None,
        help="Additional parameters to pass to the BLSCDDIR CLIST.",
    )
    create_ddir_parser.set_defaults(func=_cmd_create_ddir)

# ---------------------------------------------------------------------------
# global-defaults command
# ---------------------------------------------------------------------------

def _cmd_global_defaults(args: argparse.Namespace) -> int:
    """Run the ``global-defaults`` CLI command."""
    ddir = IpcsDdir(
        args.dsname,
        driver=args.driver,
        allocations=_parse_allocations(),
    )
    response = ddir.global_defaults(
        dump=IpcsDump(args.dump) if args.dump else None,
        parms=args.parms,
    )
    print(response.output, end="")
    sys.exit(response.rc)


def _add_global_defaults_parser(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    """Add the ``global-defaults`` subparser."""
    global_defaults_parser = subparsers.add_parser(
        "global-defaults",
        help="Set global defaults on an existing DDIR.",
    )
    global_defaults_parser.add_argument("dsname", help="Data set name of the DDIR.")
    global_defaults_parser.add_argument(
        "--driver",
        metavar="DSNAME",
        default=None,
        help="Driver data set name to use for the DDIR.",
    )
    global_defaults_parser.add_argument(
        "--dump",
        metavar="DSNAME",
        default=None,
        help="Source dump data set name to set as the global default.",
    )
    global_defaults_parser.add_argument(
        "--parms",
        default=None,
        help="Additional parameters to pass to the global defaults command.",
    )
    global_defaults_parser.set_defaults(func=_cmd_global_defaults)

# ---------------------------------------------------------------------------
# run command
# ---------------------------------------------------------------------------

def _cmd_run(args: argparse.Namespace) -> int:
    """Run the ``run`` CLI command."""
    ddir = IpcsDdir(
        args.dsname,
        driver=args.driver,
        allocations=_parse_allocations(),
    )
    response = ddir.run(
        args.subcmd,
        dump=IpcsDump(args.dump) if args.dump else None,
        authorized=args.auth,
        local_defaults=args.local_defaults,
    )
    print(response.output, end="")
    sys.exit(response.rc)


def _add_run_parser(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    """Add the ``run`` subparser."""
    run_parser = subparsers.add_parser(
        "run",
        help="Run an IPCS subcommand against an existing DDIR.",
    )
    run_parser.add_argument("subcmd", help="IPCS subcommand to run.")
    run_parser.add_argument(
        "--ddir",
        dest="dsname",
        required=True,
        metavar="DSNAME",
        help="Data set name of the DDIR.",
    )
    run_parser.add_argument(
        "--driver",
        metavar="DSNAME",
        default=None,
        help="Driver data set name to use for the DDIR.",
    )
    run_parser.add_argument(
        "--dump",
        metavar="DSNAME",
        default=None,
        help="Source dump data set name for this invocation.",
    )
    run_parser.add_argument(
        "--auth",
        action="store_true",
        default=False,
        help="Run the subcommand in an authorized environment.",
    )
    run_parser.add_argument(
        "--local-defaults",
        default=None,
        help="Parameters for SETDEF NOLIST LOCAL run before the subcommand.",
    )
    run_parser.set_defaults(func=_cmd_run)


def main() -> None:
    """CLI entry point for the ``pyipcs`` command."""
    parser = argparse.ArgumentParser(
        prog="pyipcs",
        description="pyIPCS command-line interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Custom allocations can be provided with the IPCSALLOC environment\n"
            "variable, which works identically to TSOALLOC used by tsocmd:\n\n"
            "  export IPCSALLOC=IPCSPARM:SYSPROC\n"
            "  export IPCSPARM=SYS1.PARMLIB\n"
            "  export SYSPROC=SYS1.SBLSCLI0\n\n"
            "Each DD variable is passed through verbatim, so allocation\n"
            "strings and DSN concatenations are both supported.\n\n"
            "The process exit code equals the TSO/IPCS response return code."
        ),
    )

    subparsers = parser.add_subparsers(dest="command", metavar="command")
    subparsers.required = True

    _add_create_ddir_parser(subparsers)
    _add_global_defaults_parser(subparsers)
    _add_run_parser(subparsers)

    args = parser.parse_args()
    args.func(args)
