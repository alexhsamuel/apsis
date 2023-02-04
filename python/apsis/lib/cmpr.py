import asyncio
import logging
from   pathlib import Path
import shlex

log = logging.getLogger(__name__)

BROTLI = Path("/usr/bin/brotli")

#-------------------------------------------------------------------------------

async def compress_async(data, compression) -> bytes:
    """
    Compresses `data` with `compression`.

    :raise RuntimeError:
      Compression failed.
    """
    if compression is None:
        return data

    elif compression == "br":
        argv = (str(BROTLI), "--stdout", "--quality=3")
        log.info(f"compressing: {shlex.join(argv)}")
        proc = await asyncio.create_subprocess_exec(
            *argv,
            stdin   =asyncio.subprocess.PIPE,
            stdout  =asyncio.subprocess.PIPE,
            stderr  =asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate(input=data)
        if proc.returncode == 0:
            return stdout
        else:
            raise RuntimeError("compression failed: {proc.returncode}: {stderr}")

    else:
        raise NotImplementedError(f"compression: {compression}")


