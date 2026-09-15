"""
Pytest configuration for pyIPCS
"""

import json
import warnings
from typing import Any, Iterable, Optional
from collections.abc import Generator
import pytest

from zoautil_py import datasets, jobs
from pyipcs import IpcsDump, IpcsDdir
from pyipcs._util import tso_profile_prefix, check_dataset_exists
from pyipcs.util import default_driver_dsname


# ==============================================================================
# Helper Functions
# ==============================================================================


def cleanup_test_dataset(dsname: str) -> bool:
    """Delete a data set if it exists."""
    if check_dataset_exists(dsname):
        rc = datasets.delete(dsname)
        if rc != 0:
            warnings.warn(f"Could not delete test data set '{dsname}': rc={rc}")
            return False
    return True


def cleanup_test_ddir(dsname: str) -> bool:
    """Delete a DDIR if it exists."""
    if check_dataset_exists(dsname):
        response = IpcsDdir._delete_ddir(dsname)
        if response.rc != 0:
            warnings.warn(
                f"Could not delete test data set '{dsname}': rc={response.rc}"
            )
            return False
    return True


# ==============================================================================
# Stash Keys
# ==============================================================================

DUMP_KEY: pytest.StashKey[IpcsDump | None] = pytest.StashKey()
ALLOCATIONS_KEY: pytest.StashKey[dict[str, str | list[str]] | None] = pytest.StashKey()
HLQ_KEY: pytest.StashKey[str] = pytest.StashKey()
DRIVER_DSNAME_KEY: pytest.StashKey[str] = pytest.StashKey()
DDIR_DSNAME_KEY: pytest.StashKey[str] = pytest.StashKey()
DUMP_DDIR_DSNAME_KEY: pytest.StashKey[str] = pytest.StashKey()

# ==============================================================================
# Pytest Options
# ==============================================================================


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--dump",
        action="store",
        default=None,
        metavar="DSNAME",
        help="Data set name of the dump to use in tests.",
    )
    parser.addoption(
        "--allocations",
        action="store",
        default=None,
        metavar="FILE",
        help=(
            "Path to a JSON file containing custom TSO/E allocations. "
            "The file must be a JSON object where keys are DD names and values "
            "are string allocation requests or lists of dataset names. "
            'Defaults to {"IPCSPARM": "SYS1.PARMLIB", "SYSPROC": "SYS1.SBLSCLI0"}.'
        ),
    )
    parser.addoption(
        "--hlq",
        action="store",
        default=None,
        metavar="HLQ",
        help=(
            "High-level qualifier to use in tests. "
            "Defaults to <TSO profile prefix>.PYTEST."
        ),
    )


def pytest_configure(config: pytest.Config) -> None:
    allocations_path = config.getoption("--allocations", default=None)
    if allocations_path is None:
        config.stash[ALLOCATIONS_KEY] = None
    else:
        with open(allocations_path, encoding="utf-8") as f:
            config.stash[ALLOCATIONS_KEY] = json.load(f)

    hlq = config.getoption("--hlq", default=None) or f"{tso_profile_prefix()}.PYTEST"
    config.stash[HLQ_KEY] = hlq
    config.stash[DRIVER_DSNAME_KEY] = f"{hlq}.DRIVER"
    config.stash[DDIR_DSNAME_KEY] = f"{hlq}.TESTDDIR"
    config.stash[DUMP_DDIR_DSNAME_KEY] = f"{hlq}.DUMPDDIR"

    dump_dsname = config.getoption("--dump", default=None)
    config.stash[DUMP_KEY] = None if dump_dsname is None else IpcsDump(dump_dsname)

    # Initialize dump if provided
    dump = config.stash[DUMP_KEY]
    if not cleanup_test_ddir(config.stash[DUMP_DDIR_DSNAME_KEY]):
        pytest.exit("Failed to delete test data set")
    if dump is not None:
        with IpcsDdir(
            config.stash[DUMP_DDIR_DSNAME_KEY],
            allocations=config.stash[ALLOCATIONS_KEY],
        ) as pytest_ddir:
            pytest_ddir.init_dump(dump)
            if dump.dsname not in pytest_ddir.sources():
                pytest.exit(
                    f"Failed to initialize '{dump.dsname}' in DDIR '{config.stash[DUMP_DDIR_DSNAME_KEY]}'"
                )
        if not check_dataset_exists(config.stash[DUMP_DDIR_DSNAME_KEY]):
            pytest.exit(
                f"Test dump DDIR '{config.stash[DUMP_DDIR_DSNAME_KEY]}' did not persist after dump initialization"
            )


# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture(scope="session")
def dump(request: pytest.FixtureRequest) -> IpcsDump:
    """IpcsDump built from the data set name passed via --dump. Skips the test if not provided."""
    result = request.config.stash[DUMP_KEY]
    if result is None:
        pytest.skip("--dump not provided")
    return result


@pytest.fixture(scope="session")
def allocations(request: pytest.FixtureRequest) -> dict[str, str | list[str]] | None:
    """Allocations dict loaded from the JSON file passed via ``--allocations``."""
    return request.config.stash[ALLOCATIONS_KEY]


@pytest.fixture(scope="session")
def hlq(request: pytest.FixtureRequest) -> str:
    """High-level qualifier passed via --hlq, defaulting to <tso_profile_prefix>.PYTEST."""
    return request.config.stash[HLQ_KEY]


@pytest.fixture(scope="session")
def driver_dsname(request: pytest.FixtureRequest) -> str:
    """Data set name for the non-default test pyIPCS driver."""
    return request.config.stash[DRIVER_DSNAME_KEY]


@pytest.fixture(scope="session")
def ddir_dsname(request: pytest.FixtureRequest) -> str:
    """Data set name for the general-purpose test DDIR."""
    return request.config.stash[DDIR_DSNAME_KEY]


@pytest.fixture(scope="session")
def dump_ddir_dsname(request: pytest.FixtureRequest) -> str:
    """Data set name for the dump test DDIR."""
    return request.config.stash[DUMP_DDIR_DSNAME_KEY]


@pytest.fixture(scope="session", autouse=True)
def environment(
    dump_ddir_dsname: str,
) -> Generator[None, Any, None]:
    """Test session setup and cleanup."""
    yield
    if not cleanup_test_ddir(dump_ddir_dsname):
        pytest.exit(f"Failed to delete test data sets")


@pytest.fixture(autouse=True)
def reset_state(
    hlq: str,
    driver_dsname: str,
    ddir_dsname: str,
) -> Generator[None, Any, None]:
    """Delete leftover test data sets before and after each test."""

    def cleanup_test_datasets():
        failures: list[str] = []
        for dsname in [default_driver_dsname(), driver_dsname]:
            if not cleanup_test_dataset(dsname):
                failures.append(dsname)
        if not cleanup_test_ddir(ddir_dsname):
            failures.append(ddir_dsname)
        for dataset in datasets.list_vsam_datasets(
            f"{tso_profile_prefix()}.PYIPCS.DDIR*"
        ):
            if not cleanup_test_ddir(dataset.name):
                failures.append(dataset.name)
        for dataset in datasets.list_vsam_datasets(f"{hlq}.DDIR*"):
            if not cleanup_test_ddir(dataset.name):
                failures.append(dataset.name)
        if failures:
            pytest.exit("Failed to delete test data sets")

    cleanup_test_datasets()
    yield
    cleanup_test_datasets()


@pytest.fixture
def ddir(allocations, ddir_dsname) -> Generator[IpcsDdir, None, None]:
    """DDIR with no dump initialized. DDIR deleted per test."""
    with IpcsDdir(
        ddir_dsname,
        allocations=allocations,
        delete=True,
    ) as pytest_ddir:
        yield pytest_ddir


@pytest.fixture
def dump_ddir(dump, allocations, dump_ddir_dsname) -> Generator[IpcsDdir, None, None]:
    """DDIR with dump initialized. Skips the test if no dump was provided."""
    if dump is None:
        pytest.skip("--dump not provided")
    with IpcsDdir(
        dump_ddir_dsname,
        allocations=allocations,
    ) as pytest_ddir:
        yield pytest_ddir


# ==============================================================================
# JCL IPCS Subcommand Processing
# ==============================================================================


IPCS_JCL = """//MOCKPY JOB 'MOCK PYIPCS',CLASS=A
//*====================================================================
//* PYIPCS SUBCOMMAND JCL, VALIDATE SUBCMD OUTPUT
//*====================================================================
//IPCS EXEC PGM=IKJEFT01,DYNAMNBR=1000,REGION=0M
//IPCSDDIR DD DISP=SHR,DSN={ddir}
{allocations}
//SYSUDUMP DD SYSOUT=*
//SYSTSPRT  DD DSN={jcl_dsname},DISP=OLD
//SYSTSIN DD *
PROFILE MSGID
IPCS NOPARM
{setdef}
{subcmds}
END
"""


@pytest.fixture
def ipcs_subcmd_job(
    hlq: str,
):
    """Fixture that returns a callable that executes IPCS subcommands via a submitted job.

    Returns:
        Callable: A function with the signature::

            def _ipcs_subcmd_job(
                ddir: IpcsDdir,
                subcmds: list[str],
                allocations: Optional[dict[str, str | list[str]]],
                dump: Optional[IpcsDump] = None,
                local_defaults: Optional[str | Iterable[str]] = None,
            ) -> list[str]:
    """

    def _ipcs_subcmd_job(
        ddir: IpcsDdir,
        subcmds: list[str],
        allocations: Optional[dict[str, str | list[str]]],
        dump: Optional[IpcsDump] = None,
        local_defaults: Optional[str | Iterable[str]] = None,
    ) -> list[str]:
        """Run one or more IPCS subcommands in a job and return their outputs.

        Args:
            ddir: DDIR to run subcommands against.
            subcmds: Ordered list of IPCS subcommands to run.
            allocations: DD allocations. Values must be list[str] (dataset names).
                str values are not accepted for pyIPCS JCL testing.
            dump: Dump to set via SETDEF DSNAME.
            local_defaults: Additional SETDEF defaults to apply alongside the dump.

        Returns:
            list[str]: One raw output string per entry in ``subcmds``, in order.
        """
        jcl_temp_dsname = f"{hlq}.JCLIN"
        jcl_temp_membername = f"{jcl_temp_dsname}(TMP)"
        jcl_output_dsname = f"{hlq}.JCLOUT"

        def _ipcs_subcmd_jcl() -> str:
            """Format IPCS JCL for one or more subcommands.

            Returns:
                str: Formatted JCL string.
            """
            # Build DD allocations block
            dd_lines = "//*"
            if allocations:
                parts = []
                for dd_name, specification in allocations.items():
                    if isinstance(specification, str):
                        pytest.exit(
                            f"String allocation '{specification}' for DD '{dd_name}' "
                            "is not accepted for pyIPCS JCL testing. "
                            "Use a list of dataset names instead."
                        )
                    # list[str] — dataset concatenation as JCL DD lines
                    if specification:
                        parts.append(f"//{dd_name}  DD DSN={specification[0]},DISP=SHR")
                    for dsname in specification[1:]:
                        parts.append(f"//         DD DSN={dsname},DISP=SHR")
                dd_lines = "\n".join(parts) if parts else "//*"

            # Build SETDEF line
            _local_defaults = local_defaults
            if _local_defaults is not None and not isinstance(_local_defaults, str):
                _local_defaults = " ".join(_local_defaults)

            if dump is not None:
                if _local_defaults:
                    setdef_line = f"SETDEF LOCAL LIST DSNAME('{dump.dsname}') {_local_defaults}"
                else:
                    setdef_line = f"SETDEF LOCAL LIST DSNAME('{dump.dsname}')"
            elif _local_defaults:
                setdef_line = f"SETDEF LOCAL LIST {_local_defaults}"
            else:
                setdef_line = "SETDEF LOCAL LIST"

            subcmds_block = "\n".join(subcmds)

            return IPCS_JCL.format(
                jcl_dsname=jcl_output_dsname,
                ddir=ddir.dsname,
                allocations=dd_lines,
                setdef=setdef_line,
                subcmds=subcmds_block,
            )

        def _submit_ipcs_subcmd_jcl(jcl: str) -> str:
            """Submit IPCS JCL and return the raw SYSTSPRT output.

            Args:
                jcl: Formatted JCL string to submit.

            Returns:
                str: Raw SYSTSPRT output from the job.
            """
            # Create and write JCL to temp PDSE member
            datasets.create(name=jcl_temp_dsname, dataset_type="PDSE")
            datasets.write(dataset_name=jcl_temp_membername, content=jcl)

            # Create output dataset (SYSTSPRT target)
            datasets.create(name=jcl_output_dsname, dataset_type="SEQ", record_format="VB")
            datasets.write(dataset_name=jcl_output_dsname, content="")

            # Submit and wait
            job = jobs.submit(jcl_temp_membername)
            job.wait()
            job.refresh()

            # Read output
            output = datasets.read(jcl_output_dsname)

            # Delete temp datasets
            rc_jcl = datasets.delete(jcl_temp_dsname)
            rc_out = datasets.delete(jcl_output_dsname)
            if rc_jcl != 0 or rc_out != 0:
                warnings.warn(
                    "Error deleting temp pyIPCS JCL test datasets: "
                    f"{jcl_temp_dsname} and/or {jcl_output_dsname}",
                    UserWarning,
                )

            return output

        jcl = _ipcs_subcmd_jcl()
        raw_output = _submit_ipcs_subcmd_jcl(jcl)

        # Parse each subcommand's output from the raw SYSTSPRT text.
        # SYSTSIN echoes each command as "IPCS\n<subcmd>\n"; slice between markers.
        outputs: list[str] = []
        subcmd_index = raw_output.find(f"\nIPCS\n{subcmds[0]}\n") + len(
            f"\nIPCS\n{subcmds[0]}\n"
        )
        for i in range(len(subcmds)):
            if i != len(subcmds) - 1:
                subcmd_end_index = raw_output.find(
                    f"\nIPCS\n{subcmds[i + 1]}\n", subcmd_index
                )
                subcmd_output = raw_output[subcmd_index:subcmd_end_index]
                subcmd_index = subcmd_end_index + len(f"\nIPCS\n{subcmds[i + 1]}\n")
            else:
                subcmd_end_index = raw_output.find("\nIPCS\n", subcmd_index)
                subcmd_output = (
                    raw_output[subcmd_index:subcmd_end_index]
                    if subcmd_end_index != -1
                    else raw_output[subcmd_index:]
                )
            outputs.append(subcmd_output)

        return outputs

    return _ipcs_subcmd_job

