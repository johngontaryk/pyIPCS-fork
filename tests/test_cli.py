"""
Test pyIPCS CLI command handlers
"""

import json
import tempfile
from argparse import Namespace

import pytest

from pyipcs import IpcsDdir
from pyipcs._util import check_dataset_exists
from pyipcs.cli._commands import (
    handle_create_ddir,
    handle_global_defaults,
    handle_run,
)


# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture
def allocations_path(allocations):
    """Write the allocations dict to a temp JSON file and yield its path.

    Yields ``None`` when ``allocations`` is ``None`` so callers omit the flag.
    """
    if allocations is None:
        yield None
        return
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=True, encoding="utf-8"
    ) as f:
        json.dump(allocations, f)
        f.flush()
        yield f.name


# ==============================================================================
# Helper Functions
# ==============================================================================


def _exit_code(exc: pytest.ExceptionInfo[SystemExit]) -> int:
    """Return the integer exit code from a SystemExit ExceptionInfo."""
    code = exc.value.code
    assert isinstance(code, int)
    return code


# ==============================================================================
# Tests
# ==============================================================================


def test_handle_create_ddir(ddir_dsname, allocations_path):
    """handle_create_ddir should create the DDIR and exit 0."""
    assert not check_dataset_exists(ddir_dsname)
    args = Namespace(ddir=ddir_dsname, driver=None, allocations=allocations_path, parms=None)

    with pytest.raises(SystemExit) as exc:
        handle_create_ddir(args)

    assert _exit_code(exc) == 0
    assert check_dataset_exists(ddir_dsname)


def test_handle_create_ddir_with_parms(ddir_dsname, allocations_path):
    """handle_create_ddir should forward parms to IpcsDdir and exit 0."""
    assert not check_dataset_exists(ddir_dsname)
    args = Namespace(ddir=ddir_dsname, driver=None, allocations=allocations_path, parms="LENGTH(8) NOCONFIRM")

    with pytest.raises(SystemExit) as exc:
        handle_create_ddir(args)

    assert _exit_code(exc) == 0
    assert check_dataset_exists(ddir_dsname)


def test_handle_global_defaults(ddir_dsname, allocations, allocations_path, capsys):
    """handle_global_defaults should set defaults and exit with rc < 8."""
    with IpcsDdir(ddir_dsname, allocations=allocations):
        pass
    args = Namespace(ddir=ddir_dsname, driver=None, allocations=allocations_path, dump=None, parms=None)

    with pytest.raises(SystemExit) as exc:
        handle_global_defaults(args)

    assert _exit_code(exc) < 8
    assert "LENGTH(4)" in capsys.readouterr().out


def test_handle_global_defaults_with_parms(ddir_dsname, allocations, allocations_path, capsys):
    """handle_global_defaults should forward parms and exit with rc < 8."""
    with IpcsDdir(ddir_dsname, allocations=allocations):
        pass
    args = Namespace(ddir=ddir_dsname, driver=None, allocations=allocations_path, dump=None, parms="LENGTH(8) NOCONFIRM")

    with pytest.raises(SystemExit) as exc:
        handle_global_defaults(args)

    assert _exit_code(exc) < 8
    out = capsys.readouterr().out
    assert "LENGTH(8)" in out
    assert "NOCONFIRM" in out


def test_handle_global_defaults_with_dump(dump, dump_ddir_dsname, allocations_path, capsys):
    """handle_global_defaults should set the dump as global default when dump is given."""
    args = Namespace(ddir=dump_ddir_dsname, driver=None, allocations=allocations_path, dump=dump.dsname, parms=None)

    with pytest.raises(SystemExit) as exc:
        handle_global_defaults(args)

    assert _exit_code(exc) < 8
    assert f"DSNAME('{dump.dsname}')" in capsys.readouterr().out


def test_handle_run(ddir_dsname, allocations, allocations_path, capsys):
    """handle_run should run the subcommand and exit with rc < 8."""
    with IpcsDdir(ddir_dsname, allocations=allocations):
        pass
    args = Namespace(
        ddir=ddir_dsname, driver=None, allocations=allocations_path,
        subcmd="SETDEF LIST", dump=None, auth=False, local_defaults=None,
    )

    with pytest.raises(SystemExit) as exc:
        handle_run(args)

    assert _exit_code(exc) < 8
    assert "LENGTH(4)" in capsys.readouterr().out


def test_handle_run_with_dump(dump, dump_ddir_dsname, allocations_path, capsys):
    """handle_run should include the dump in the subcommand run when dump is given."""
    args = Namespace(
        ddir=dump_ddir_dsname, driver=None, allocations=allocations_path,
        subcmd="SETDEF LIST", dump=dump.dsname, auth=False, local_defaults=None,
    )

    with pytest.raises(SystemExit) as exc:
        handle_run(args)

    assert _exit_code(exc) < 8
    assert f"DSNAME('{dump.dsname}')" in capsys.readouterr().out


def test_handle_run_authorized(ddir_dsname, allocations, allocations_path):
    """handle_run should run the subcommand in an authorized environment."""
    with IpcsDdir(ddir_dsname, allocations=allocations):
        pass
    args = Namespace(
        ddir=ddir_dsname, driver=None, allocations=allocations_path,
        subcmd="SETDEF LIST", dump=None, auth=True, local_defaults=None,
    )

    with pytest.raises(SystemExit) as exc:
        handle_run(args)

    assert _exit_code(exc) < 8


def test_handle_run_local_defaults(ddir_dsname, allocations, allocations_path, capsys):
    """handle_run should apply local_defaults for this run only."""
    with IpcsDdir(ddir_dsname, allocations=allocations):
        pass
    args = Namespace(
        ddir=ddir_dsname, driver=None, allocations=allocations_path,
        subcmd="SETDEF LIST", dump=None, auth=False, local_defaults="LENGTH(8) NOCONFIRM",
    )

    with pytest.raises(SystemExit) as exc:
        handle_run(args)

    assert _exit_code(exc) < 8
    out = capsys.readouterr().out
    assert "LENGTH(8)" in out
    assert "NOCONFIRM" in out
