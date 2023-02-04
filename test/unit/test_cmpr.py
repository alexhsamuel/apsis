import brotli
import pytest

from   apsis.lib.cmpr import compress_async

#-------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_compress_async():
    data = b"alkjsdhtlkqjhwetrnabsdcvlkjhqaweljkh" * 1024

    compressed = await compress_async(data, None)
    assert compressed == data

    compressed = await compress_async(data, "br")
    assert len(compressed) < len(data)
    assert brotli.decompress(compressed) == data


