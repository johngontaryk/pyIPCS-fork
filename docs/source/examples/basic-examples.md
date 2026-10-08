# Basic Examples

The typical pyIPCS workflow:

1. **Open a DDIR** with `IpcsDdir`
2. **Reference a dump** with `IpcsDump`
3. **Run subcommands** via `ddir.run()` and inspect the `IpcsResponse`

## Your First Dump Analysis

```python
from pyipcs import IpcsDdir, IpcsDump

DUMP_DSNAME = "MY.DUMP.DSNAME"
DDIR_DSNAME = "MY.IPCS.DDIR"

with IpcsDdir(DDIR_DSNAME) as ddir:
    dump = IpcsDump(DUMP_DSNAME)

    # Run a subcommand against the dump
    response = ddir.run("STATUS FAILDATA", dump=dump)

    print(f"Return code: {response.rc}")
    print(response.output)
```

## Using a Temporary DDIR

For one-off analysis, use `IpcsDdir.tempddir()` to create a temporary DDIR that is
automatically deleted on exit:

```python
from pyipcs import IpcsDdir, IpcsDump

with IpcsDdir.tempddir() as ddir:
    dump = IpcsDump("MY.DUMP.DSNAME")
    response = ddir.run("STATUS REGISTERS", dump=dump)
    print(response.output)
```

## Inspecting Dump Metadata

`IpcsDump` parses the dump header on initialization:

```python
from pyipcs import IpcsDump

dump = IpcsDump("MY.DUMP.DSNAME")

if dump.metadata:
    print(f"Type:      {dump.metadata['type']}")
    print(f"Title:     {dump.metadata['title']}")
    print(f"System:    {dump.metadata['sysname']}")
    print(f"z/OS:      {dump.metadata['version']}.{dump.metadata['release']}")
    print(f"Timestamp: {dump.metadata['timestamp']}")
```

## Using pyipcs.ipcs Utility Functions

The `pyipcs.ipcs` module provides convenience functions that run common subcommands
and return parsed results:

```python
from pyipcs import IpcsDdir, IpcsDump
from pyipcs import ipcs

with IpcsDdir.tempddir() as ddir:
    dump = IpcsDump("MY.DUMP.DSNAME")

    # List all address spaces on the system at dump time
    asids = ipcs.select_all(ddir, dump)
    if asids:
        for entry in asids:
            print(f"ASID: {entry['asid']}  Job: {entry['jobname']}  ASCB: {entry['ascb']}")

    # Get IPL time
    ipl = ipcs.ipltime(ddir, dump)
    print(f"IPL time: {ipl}")

    # Decode an opcode
    mnemonic = ipcs.opcode(ddir, dump, "0A0A")
    print(f"Mnemonic: {mnemonic}")
```

## Writing Subcommand Output to a File

For large subcommand outputs, write directly to a file instead of buffering in memory:

```python
from pyipcs import IpcsDdir, IpcsDump

with IpcsDdir.tempddir() as ddir:
    dump = IpcsDump("MY.DUMP.DSNAME")

    with open("/tmp/output.txt", "w", encoding="cp1047") as f:
        ddir.run("SELECT ALL", dump=dump, output=f)
```

## Best Practices

1. **Use `IpcsDdir` as a context manager** — ensures resources are cleaned up properly
2. **Use `IpcsDdir.tempddir()`** for one-off analysis to avoid managing DDIR data set names
3. **Pass `dump` per `run()` call** rather than using `setdef_global` unless you have exclusive DDIR access
4. **Check `IpcsResponse.rc`** — a non-zero return code may indicate a subcommand issue
