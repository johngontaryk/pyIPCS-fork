"""
IPCS Utility Functions
"""

from __future__ import annotations
import datetime
from typing import Optional, TYPE_CHECKING

from zoautil_py import zoau_io  # pylint: disable=import-error
from ._util import get_dataset

if TYPE_CHECKING:
    from .ddir import IpcsDdir
    from .dump import IpcsDump


def is_dump(dsname: str) -> bool:
    """
    Determine whether a data set exists and is a z/OS dump data set.

    Args:
        dsname: Data set name.

    Returns:
        bool: ``True`` if the data set exists and is a dump data set,
        ``False`` otherwise.
    """
    # Check if the data set exists and perform checks
    dump_dataset_obj = get_dataset(dsname)
    if dump_dataset_obj is None:
        return False
    if int(dump_dataset_obj.record_length) != 4160:
        return False
    if int(dump_dataset_obj.block_size) % int(dump_dataset_obj.record_length) != 0:
        return False
    # Check if first record starts with DR2
    if (
        not zoau_io.RecordIO(f"//'{dsname}'")
        .readrecord()
        .hex()
        .upper()
        .startswith("C4D9F2")
    ):
        return False
    return True


def sliptrap(ddir: IpcsDdir, dump: IpcsDump) -> Optional[str]:
    """
    Run ``LIST SLIPTRAP`` and return the SLIPTRAP string for the dump.

    Args:
        ddir: DDIR to run the subcommand against.
        dump: Dump data set to run the subcommand against.

    Returns:
        str | None: The SLIPTRAP string, ``None`` if there is no SLIPTRAP,
        or ``None`` if the dump is not a SLIP dump or the subcommand return
        code is greater than 0.
    """
    if dump.metadata is None or dump.metadata.get("type") != "SLIP":
        return None

    response = ddir.run("LIST SLIPTRAP", dump=dump)
    if response.rc > 0 or response.output is None:
        return None

    sliptrap_lines = response.output.splitlines()

    # If the number of lines is 1 or less there is no SLIPTRAP
    if len(sliptrap_lines) <= 1:
        return None

    # Remove first 3 lines to get to SLIPTRAP content
    sliptrap_lines = sliptrap_lines[3:]

    # SLIPTRAP text is between '| ' and ' |'
    result = ""
    for line in sliptrap_lines:
        start = line.find("| ")
        if start == -1:
            continue
        result += line[start + len("| ") : len(line) - len(" |")]

    return result if result else None


def ipl_time(ddir: IpcsDdir, dump: IpcsDump) -> Optional[str]:
    """
    Run ``IPLDATA`` and return the local IPL date/time in ISO 8601 format.

    Args:
        ddir: DDIR to run the subcommand against.
        dump: Dump data set to run the subcommand against.

    Returns:
        str | None: ISO 8601 datetime string (``YYYY-MM-DDTHH:MM:SS``) of the
        local IPL time, or ``None`` if the information could not be determined
        or the subcommand return code is greater than 0.
    """
    response = ddir.run("IPLDATA", dump=dump)
    if response.rc > 0 or response.output is None:
        return None

    output = response.output
    marker = "System IPLed at "
    idx = output.find(marker)
    if idx == -1:
        return None

    idx += len(marker)
    end = output.find("\n", idx)
    line = output[idx:end].strip() if end != -1 else output[idx:].strip()

    # Line format: "HH:MM:SS on MM/DD/YYYY"
    try:
        time_str, date_str = line.split(" on ")
        dt = datetime.datetime.strptime(
            f"{date_str.strip()} {time_str.strip()}", "%m/%d/%Y %H:%M:%S"
        )
        return dt.isoformat()
    except (ValueError, AttributeError):
        return None


def select_all(ddir: IpcsDdir, dump: IpcsDump) -> Optional[list[dict]]:
    """
    Run ``SELECT ALL`` and return a list of ASIDs on the system at dump time.

    Args:
        ddir: DDIR to run the subcommand against.
        dump: Dump data set to run the subcommand against.

    Returns:
        list[dict] | None: List of dictionaries, each with keys:

        - **"asid"** (str): Hex ASID string.
        - **"jobname"** (str | None): Job name, or ``None`` if unavailable.
        - **"ascb"** (str): Hex ASCB address string.

        Returns ``None`` if the subcommand return code is greater than 0 or
        the output could not be parsed.
    """
    response = ddir.run("SELECT ALL", dump=dump)
    if response.rc > 0 or response.output is None:
        return None

    output = response.output
    header_marker = "ASID JOBNAME  ASCBADDR  SELECTION CRITERIA"
    idx = output.find(header_marker)
    if idx == -1:
        return None

    # Skip header line and separator line
    asid_lines = output[idx:].splitlines()[2:]

    asids_all = []
    for line in asid_lines:
        asid = line[1:5].strip()
        jobname = line[6:14].strip() or None
        ascb = line[15:24].strip()
        asids_all.append({"asid": asid, "jobname": jobname, "ascb": ascb})

    return asids_all


def storage_areas(ddir: IpcsDdir, dump: IpcsDump) -> Optional[dict]:
    """
    Run ``LISTDUMP SELECT DSNAME`` and return all ASIDs and data spaces included in the dump.

    Args:
        ddir: DDIR to run the subcommand against.
        dump: Dump data set to run the subcommand against.

    Returns:
        dict | None: Dictionary with keys:

        - **"asids"** (list[str]): List of hex ASID strings present in the dump.
        - **"dspnames"** (dict[str, list[str]]): Mapping of hex ASID string to a
          list of data space names dumped for that ASID. ASIDs without a data space
          are not included.

        Returns ``None`` if the subcommand return code is greater than 0 or
        the output could not be parsed.
    """
    response = ddir.run(f"LISTDUMP SELECT DSNAME('{dump.dsname}')", dump=dump)
    if response.rc > 0 or response.output is None:
        return None

    output = response.output
    asids: set[str] = set()
    dspnames: dict[str, list[str]] = {}
    pos = 0

    while True:
        idx = output.find("bytes described in", pos)
        if idx == -1:
            break

        line = output[output.rfind("\n", 0, idx) + 1 : output.find("\n", idx)]
        pos = idx + 1

        if "ASID" not in line:
            continue

        asid_start = line.find("ASID(X'") + 7
        asid = line[asid_start : line.find("')", asid_start)]
        asids.add(asid)

        if "DSPNAME" in line:
            if asid not in dspnames:
                dspnames[asid] = []
            dspname_start = line.find("DSPNAME(") + 8
            dspnames[asid].append(line[dspname_start : line.find(")", dspname_start)])

    return {"asids": list(asids), "dspnames": dspnames}


def asids_dumped(ddir: IpcsDdir, dump: IpcsDump) -> Optional[list[str]]:
    """
    Run ``CBF RTCT`` and return the list of requested ASIDs that were dumped.

    Args:
        ddir: DDIR to run the subcommand against.
        dump: Dump data set to run the subcommand against.

    Returns:
        list[str] | None: List of hex ASID strings that were dumped, or
        ``None`` if the subcommand return code is greater than 0 or the
        output could not be parsed.
    """
    response = ddir.run("CBF RTCT", dump=dump)
    if response.rc > 0 or response.output is None:
        return None

    marker = "SDAS  SDF4  SDF5"
    idx = response.output.find(marker)
    if idx == -1:
        return None

    # Skip the header line and separator line, take up to 16 ASID lines
    asid_lines = response.output[idx:].splitlines()[2:18]

    asids = []
    for line in asid_lines:
        parts = line.split()
        if len(parts) < 2:
            break
        asid = parts[1]
        if asid == "0000":
            break
        asids.append(asid)

    return asids


def opcode(ddir: IpcsDdir, dump: IpcsDump, instr: str) -> Optional[str]:
    """
    Run ``OPCODE`` and return the mnemonic for an instruction.

    Args:
        ddir: DDIR to run the subcommand against.
        dump: Dump data set to run the subcommand against.
        instr: Hex string of the instruction opcode (e.g. ``"0A0A"``).

    Returns:
        str | None: The instruction mnemonic, or ``None`` if the mnemonic
        could not be determined or the subcommand return code is greater
        than 0.
    """
    response = ddir.run(f"OPCODE {instr}", dump=dump)
    if response.rc > 0 or response.output is None:
        return None
    if "IKJ56702I INVALID VARIABLE MNEMONIC OPTION" in response.output:
        return None

    marker = f"Mnemonic for X'{instr}' is "
    idx = response.output.find(marker)
    if idx == -1:
        return None

    mnemonic = response.output[idx + len(marker) :].rstrip()
    return mnemonic if mnemonic else None
