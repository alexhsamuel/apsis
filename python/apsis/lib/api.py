import brotli
import gzip
import logging
import sanic
import zlib

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

def response_json(jso, status=200):
    return sanic.response.json(
        jso,
        status=status, indent=0, escape_forward_slashes=False,
    )


def error(message, status=400, **kw_args):
    return response_json({"error": str(message), **kw_args}, status=status)


def time_to_jso(time):
    return format(time, "%.3i")


def to_bool(string):
    if string in {"True", "true", "T", "t"}:
        return True
    elif string in {"False", "false", "F", "f"}:
        return False
    else:
        raise ValueError(f"unknown bool: {string}")


def decompress(data, compression) -> bytes:
    """
    Decompresses `data` assuming it is compressed with `compression`.
    """
    match compression:
        case "br":
            data = brotli.decompress(data)
        case "deflate":
            data = zlib.decompress(data)
        case "gzip":
            data = gzip.decompress(data)
        case None:
            pass
        case _:
            raise RuntimeError(f"can't decompress: {compression}")
    return data


def encode_response(headers, data, compression):
    """
    Encodes data for a response.

    :param headers:
      Request headers.
    :param data:
      Response data bytes.
    :param compression:
      Current compression of data.
    :return:
      Header dict for the response, and the payload data.
    """
    accept = headers.get("Accept-Encoding", "*")
    # Split fields, and drop quality values.
    accept = { p.strip().split(";")[0] for p in accept.split(",") }

    if "*" in accept or compression in accept:
        # The current compression is accepted.
        encoding = compression

    else:
        # Use identity, which is always implicitly acceptable.
        data = decompress(data, compression)
        encoding = "identity"

    return {"Content-Encoding": encoding}, data


#-------------------------------------------------------------------------------

def run_to_summary_jso(run):
    jso = run._summary_jso_cache
    if jso is not None:
        # Use the cached JSO.
        return jso

    jso = {
        "job_id"        : run.inst.job_id,
        "args"          : run.inst.args,
        "run_id"        : run.run_id,
        "state"         : run.state.name,
        "times"         : { n: time_to_jso(t) for n, t in run.times.items() },
        "labels"        : run.meta.get("labels", []),
    }
    if run.expected:
        jso["expected"] = run.expected

    run._summary_jso_cache = jso
    return jso


#-------------------------------------------------------------------------------

def make_run_delete(run):
    return {
        "type"          : "run_delete",
        "run_id"        : run.run_id,
    }


def make_run_summary(run):
    return {
        "type"          : "run_summary",
        "run_summary"   : run_to_summary_jso(run),
    }


