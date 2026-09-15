"""
Test IpcsDdir constructor
"""

from zoautil_py import datasets
from pyipcs import IpcsDdir
from pyipcs.util import default_driver_dsname
from pyipcs._execs import IPCSVERS, IPCSRUN, IPCSSRC, IPCSEVAL
from pyipcs._util import check_dataset_exists, tso_profile_prefix


def _assert_driver(dsname: str) -> None:
    """Assert that a driver dataset exists and contains the correct execs."""
    assert check_dataset_exists(dsname)

    members = datasets.list_members(dsname)
    expected_members = ["IPCSVERS", "IPCSRUN", "IPCSSRC", "IPCSEVAL"]
    for member in expected_members:
        assert member in members, f"Member {member} is missing from driver {dsname}"

    def _assert_exec(member_name: str, expected_content: str) -> None:
        """Read and check the contents of the exec member."""
        content = datasets.read(f"{dsname}({member_name})")
        normalize = lambda s: "\n".join(line.rstrip() for line in s.splitlines()).strip()
        assert (
            normalize(content) == normalize(expected_content)
        ), f"Content of {member_name} does not match expected content"

    _assert_exec("IPCSVERS", IPCSVERS)
    _assert_exec("IPCSRUN", IPCSRUN)
    _assert_exec("IPCSSRC", IPCSSRC)
    _assert_exec("IPCSEVAL", IPCSEVAL)


def test_ddir_init_default(ddir_dsname, allocations):
    """Test default IpcsDdir constructor"""
    default_driver = default_driver_dsname()
    assert not check_dataset_exists(default_driver)
    assert not check_dataset_exists(ddir_dsname)

    # Create DDIR
    with IpcsDdir(ddir_dsname, allocations=allocations) as ddir:
        assert ddir.dsname == ddir_dsname
        assert check_dataset_exists(ddir_dsname)
        assert ddir.driver == default_driver
        _assert_driver(default_driver)

    # Check DDIR and driver persist after DDIR creation
    assert check_dataset_exists(ddir_dsname)
    _assert_driver(default_driver)

    # Check we can reuse DDIR and driver
    with IpcsDdir(ddir_dsname, allocations=allocations) as ddir:
        assert ddir.dsname == ddir_dsname
        assert check_dataset_exists(ddir_dsname)
        assert ddir.driver == default_driver
        _assert_driver(default_driver)


def test_ddir_init_custom_driver(ddir_dsname, driver_dsname, allocations):
    """Test IpcsDdir constructor with a custom driver."""
    assert not check_dataset_exists(driver_dsname)
    assert not check_dataset_exists(ddir_dsname)

    # Create DDIR
    with IpcsDdir(
        ddir_dsname, driver=driver_dsname, allocations=allocations
    ) as ddir:
        assert ddir.dsname == ddir_dsname
        assert check_dataset_exists(ddir_dsname)
        assert ddir.driver == driver_dsname
        _assert_driver(driver_dsname)

    # Check DDIR and driver persist after DDIR creation
    assert check_dataset_exists(ddir_dsname)
    _assert_driver(driver_dsname)

    # Check we can reuse DDIR and driver
    with IpcsDdir(
        ddir_dsname, driver=driver_dsname, allocations=allocations
    ) as ddir:
        assert ddir.dsname == ddir_dsname
        assert check_dataset_exists(ddir_dsname)
        assert ddir.driver == driver_dsname
        _assert_driver(driver_dsname)


def test_ddir_init_delete(ddir_dsname, allocations):
    """Test IpcsDdir constructor with delete parameter set to ``True``"""
    default_driver = default_driver_dsname()
    assert not check_dataset_exists(default_driver)
    assert not check_dataset_exists(ddir_dsname)

    # Create DDIR using with
    with IpcsDdir(ddir_dsname, allocations=allocations, delete=True) as ddir:
        assert ddir.dsname == ddir_dsname
        assert check_dataset_exists(ddir_dsname)

    # Check DDIR is deleted
    assert not check_dataset_exists(ddir_dsname)

    # Create DDIR using regular construction
    ddir = IpcsDdir(ddir_dsname, allocations=allocations, delete=True)
    assert ddir.dsname == ddir_dsname
    assert check_dataset_exists(ddir_dsname)

    # Delete object and check DDIR does not exist
    del ddir
    assert not check_dataset_exists(ddir_dsname)


def test_ddir_temp(hlq, allocations):
    """Test tempddir classmethod alternate IpcsDdir constructor"""

    with IpcsDdir.tempddir(allocations=allocations) as ddir:
        temp_ddir_dsname = ddir.dsname
        assert temp_ddir_dsname.startswith(tso_profile_prefix())
        assert check_dataset_exists(temp_ddir_dsname)
    assert not check_dataset_exists(temp_ddir_dsname)

    with IpcsDdir.tempddir(hlq=hlq, allocations=allocations) as ddir:
        temp_ddir_dsname = ddir.dsname
        assert temp_ddir_dsname.startswith(hlq)
        assert check_dataset_exists(temp_ddir_dsname)
    assert not check_dataset_exists(temp_ddir_dsname)

    # Test multiple temp DDIRs existing at once
    with IpcsDdir.tempddir(allocations=allocations) as ddir1:
        with IpcsDdir.tempddir(allocations=allocations) as ddir2:
            temp_ddir_dsname1 = ddir1.dsname
            temp_ddir_dsname2 = ddir2.dsname
            assert temp_ddir_dsname1 != temp_ddir_dsname2
            assert check_dataset_exists(temp_ddir_dsname1)
            assert check_dataset_exists(temp_ddir_dsname2)
    assert not check_dataset_exists(temp_ddir_dsname1)
    assert not check_dataset_exists(temp_ddir_dsname2)
