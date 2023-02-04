import asyncio
import brotli
from   concurrent.futures import ThreadPoolExecutor
import logging

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

async def compress_async(data, compression) -> bytes:
    """
    Compresses `data` with `compression`.
    """
    if compression is None:
        return data

    elif compression == "br":
        loop = asyncio.get_running_loop()

        with ThreadPoolExecutor(1) as executor:
            log.info(f"starting compression: {len(data)} bytes")
            return await loop.run_in_executor(
                executor, lambda: brotli.compress(data, quality=3))

    else:
        raise NotImplementedError(f"compression: {compression}")


