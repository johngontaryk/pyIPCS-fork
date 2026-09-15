"""
File for using JCL to create MockSubcmd Objects
"""

# pylint: disable=consider-using-join
import warnings
from zoautil_py import jobs, datasets
from .mock_subcmd import MockSubcmd
from .conftest import TEST_HLQ

JCL_TEMP_DSNAME = f"{TEST_HLQ}.JCLIN"

JCL_TEMP_MEMBERNAME = f"{JCL_TEMP_DSNAME}(TMP)"

JCL_OUTPUT_DSNAME = f"{TEST_HLQ}.JCLOUT"


MOCK_SUBCMD_JCL = """//MOCKPY JOB 'MOCK PYIPCS',CLASS=A
//*====================================================================
//* MOCK PYIPCS SUBCOMMAND OBJECT JCL
//*====================================================================
//IPCS EXEC PGM=IKJEFT01,DYNAMNBR=1000,REGION=0M
//IPCSDDIR DD DISP=SHR,DSN={ddir}
{dd_allocations_jcl}
//SYSUDUMP DD SYSOUT=*
//SYSTSPRT  DD DSN={mock_subcmd_dsname},DISP=OLD
//SYSTSIN DD *
PROFILE MSGID
{alloc_cmd_allocations_jcl}
IPCS NOPARM
SETDEF {dsname_param} LIST
{subcmds}
END
"""


def mock_subcmd_jcl(
    test_ddir: str,
    test_allocations: dict[str, str | list[str]],
    test_subcmds: list[str],
    test_dsname: str = "",
) -> list[MockSubcmd]:
    """
    Uses JCL to create MockSubcmd objects

    Parameters
    ----------
    test_ddir : str
        Existing DDIR to run subcommands against

    test_allocations : dict[str,str|list[str]]

    test_subcmds : list[str]

    test_dsname : str, optional
        Use dsname string to specify `SETDEF DSNAME..` (Run subcommands against particular dump).
        Default is to empty string for `SETDEF NODSNAME..`.

    Returns
    -------
    list[MockSubcmd]: list of mock Subcmd objects where 'test_subcmds[i]'
        corresponds to 'returned_list[i]'
    """

    def format_allocations(allocations) -> tuple[str, str]:
        """
        Format allocations for JCL.

        Each value can be:
          - list[str]  -> dataset name(s) to concatenate as JCL DD statements
          - str        -> TSO ALLOC command string; emitted as an ALLOC command
                         inside SYSTSIN (before IPCS is invoked)

        Returns
        -------
        tuple[str, str]
            (dd_jcl, alloc_cmds) where dd_jcl is the block of JCL DD lines and
            alloc_cmds is the block of TSO ALLOC commands for SYSTSIN.
        """
        dd_str = ""
        alloc_str = ""
        for dd_name, specification in allocations.items():
            if isinstance(specification, str):
                # TSO ALLOC command — strip leading 'alloc' verb if present,
                # then re-emit with FI(ddname) so the DD name is explicit.
                cmd = specification.strip()
                cmd_upper = cmd.upper()
                if cmd_upper.startswith("ALLOC "):
                    cmd = cmd[6:].strip()
                alloc_str += f"ALLOC FI({dd_name}) {cmd}\n"
            else:
                # list[str] — dataset concatenation as JCL DD lines
                if specification:
                    dd_str += f"//{dd_name}  DD DSN={specification[0]},DISP=SHR\n"
                for dsname in specification[1:]:
                    dd_str += f"//         DD DSN={dsname},DISP=SHR\n"
        return dd_str.rstrip("\n"), alloc_str.rstrip("\n")

    def submit_jcl():
        """
        Submit JCL and get output
        """

        # Create IPCS JCL

        jcl_subcmd_str = ""
        for subcmd in test_subcmds:
            jcl_subcmd_str += f"{subcmd}\n"

        dd_allocations_jcl, alloc_cmd_allocations_jcl = (
            format_allocations(test_allocations) if test_allocations else ("//*", "")
        )

        jcl_str = MOCK_SUBCMD_JCL.format(
            ddir=test_ddir,
            dd_allocations_jcl=dd_allocations_jcl if dd_allocations_jcl else "//*",
            alloc_cmd_allocations_jcl=alloc_cmd_allocations_jcl,
            mock_subcmd_dsname=JCL_OUTPUT_DSNAME,
            dsname_param=f"DSN('{test_dsname}')" if test_dsname else "NODSNAME",
            subcmds=jcl_subcmd_str,
        )

        # Create and write JCL to data set
        datasets.create(name=JCL_TEMP_DSNAME, dataset_type="PDSE")
        datasets.write(dataset_name=JCL_TEMP_MEMBERNAME, content=jcl_str)

        # Create JCL output dataset

        datasets.create(name=JCL_OUTPUT_DSNAME, dataset_type="SEQ", record_format="VB")
        datasets.write(dataset_name=JCL_OUTPUT_DSNAME, content="")

        # Submit job

        job = jobs.submit(JCL_TEMP_MEMBERNAME)
        job.wait()
        job.refresh()

        # Get job output

        job_output = datasets.read(JCL_OUTPUT_DSNAME)

        # Delete JCL datasets

        rc_jcl = datasets.delete(JCL_TEMP_DSNAME)
        rc_out = datasets.delete(JCL_OUTPUT_DSNAME)
        if rc_jcl != 0 or rc_out != 0:
            warnings.warn(
                "Error in Deleting Temp pyIPCS JCL Test Datasets: "
                f"{JCL_TEMP_DSNAME} and/or {JCL_OUTPUT_DSNAME}",
                UserWarning,
            )

        # Return job output

        return job_output

    job_output = submit_jcl()

    # ==============================
    # Parse Output
    # ==============================

    mock_subcmd_list = []
    subcmd_index = job_output.find(f"\nIPCS\n{test_subcmds[0]}\n") + len(
        f"\nIPCS\n{test_subcmds[0]}\n"
    )
    # pylint: disable=consider-using-enumerate
    for i in range(len(test_subcmds)):
        if i != len(test_subcmds) - 1:
            subcmd_end_index = job_output.find(
                f"\nIPCS\n{test_subcmds[i+1]}\n", subcmd_index
            )
            mock_subcmd_list.append(
                MockSubcmd(
                    job_output[subcmd_index:subcmd_end_index],
                    mock_subcmd=test_subcmds[i],
                )
            )
            subcmd_index = subcmd_end_index + len(f"\nIPCS\n{test_subcmds[i+1]}\n")
        else:
            subcmd_end_index = job_output.find("\nIPCS\n", subcmd_index)
            mock_subcmd_list.append(
                MockSubcmd(
                    job_output[subcmd_index:subcmd_end_index],
                    mock_subcmd=test_subcmds[i],
                )
            )

    return mock_subcmd_list
