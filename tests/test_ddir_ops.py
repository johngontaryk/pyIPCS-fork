"""
Test various DDIR operations
"""

import pytest
from pyipcs._util import check_dataset_exists
from pyipcs.exceptions import DdirDeletedError


def test_ddir_delete(ddir_dsname, ddir):
    """Test IpcsDdir method delete"""
    assert check_dataset_exists(ddir_dsname)
    response = ddir.delete()
    assert response.rc == 0
    assert not check_dataset_exists(ddir_dsname)
    assert ddir.is_deleted
    with pytest.raises(DdirDeletedError):
        ddir.delete()
    with pytest.raises(DdirDeletedError):
        ddir.sources()
    with pytest.raises(DdirDeletedError):
        ddir.set_global_defaults()
    with pytest.raises(DdirDeletedError):
        ddir.run("SETDEF LIST")


def test_ddir_dump_delete(ddir_dsname, dump, ddir, dump_ddir):
    """Test DDIR dump methods display DdirDeletedError"""
    assert check_dataset_exists(ddir_dsname)
    response = ddir.delete()
    assert response.rc == 0
    assert not check_dataset_exists(ddir_dsname)
    assert ddir.is_deleted
    with pytest.raises(DdirDeletedError):
        ddir.init_dump(dump)
    with pytest.raises(DdirDeletedError):
        ddir.copy_ddir(dump_ddir, dump)


def test_ddir_allocations(ddir):
    """Test IpcsDdir allocations"""
    new_allocations = {"PYTEST": ["PYTEST"]}
    ddir.set_allocations(new_allocations)
    assert ddir.allocations == new_allocations
    new_allocations["PYTEST2"] = ["PYTEST2"]
    assert ddir.allocations != new_allocations


def test_copy_ddir_drop_dump(dump, ddir, dump_ddir):
    """Test DDIR source management"""
    assert not ddir.sources()
    assert dump.dsname in dump_ddir.sources()
    ddir.copy_ddir(dump_ddir, dump)
    assert dump.dsname in ddir.sources()
    ddir.drop_dump(dump.dsname)
    assert dump.dsname not in ddir.sources()


def test_ddir_set_global_defaults(ddir):
    """Test IpcsDdir set_global_defaults method"""
    response = ddir.set_global_defaults()
    assert response.rc < 8
    assert response.output.find("LENGTH(4)") != -1
    assert response.output.find(" CONFIRM") != -1

    response = ddir.set_global_defaults(parms="LENGTH(8) NOCONFIRM")
    assert response.rc < 8
    assert response.output.find("LENGTH(8)") != -1
    assert response.output.find("NOCONFIRM") != -1

    response = ddir.set_global_defaults(parms=["LENGTH(4)", "CONFIRM"])
    assert response.rc < 8
    assert response.output.find("LENGTH(4)") != -1
    assert response.output.find(" CONFIRM") != -1

    response = ddir.set_global_defaults(parms=("LENGTH(8)", "NOCONFIRM"))
    assert response.rc < 8
    assert response.output.find("LENGTH(8)") != -1
    assert response.output.find("NOCONFIRM") != -1

    response = ddir.set_global_defaults(parms={"LENGTH(4)", "CONFIRM"})
    assert response.rc < 8
    assert response.output.find("LENGTH(4)") != -1
    assert response.output.find(" CONFIRM") != -1


def test_ddir_dump_set_global_defaults(dump, dump_ddir):
    """Test IpcsDdir set_global_defaults method dump parameter"""
    response = dump_ddir.set_global_defaults(parms="NODSNAME")
    assert response.rc < 8
    assert response.output.find("NODSNAME") != -1
    
    response = dump_ddir.set_global_defaults(dump=dump)
    assert response.rc < 8
    assert response.output.find(f"DSNAME('{dump.dsname}')") != -1
