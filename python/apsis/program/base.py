from   dataclasses import dataclass

from   apsis.lib.api import decompress
from   apsis.lib.json import TypedJso, check_schema
from   apsis.lib.parse import parse_duration
from   apsis.lib.py import format_repr
from   apsis.lib.sys import to_signal
from   apsis.runs import template_expand

#-------------------------------------------------------------------------------

class OutputMetadata:

    def __init__(self, name: str, length: int, *, 
                 content_type="application/octet-stream"):
        """
        :param name:
          User-visible output name.
        :param length:
          Length in bytes.
        :param content_type:
          MIME type of output.
        """
        self.name           = str(name)
        self.length         = int(length)
        self.content_type   = str(content_type)



class Output:

    def __init__(self, metadata: OutputMetadata, data: bytes, compression=None):
        """
        :param metadata:
          Information about the data.
        :param data:
          The data bytes; these may be compressed.
        :pamam compression:
          The compresison type, or `None` for uncompressed.
        """
        if not isinstance(data, bytes):
            raise TypeError("data must be bytes")

        self.metadata       = metadata
        self.data           = data
        self.compression    = compression


    def get_uncompressed_data(self) -> bytes:
        """
        Returns the output data, decompressing if necessary.
        """
        return decompress(self.data, self.compression)



def program_outputs(output: bytes, *, length=None, compression=None):
    if length is None:
        length = len(output)
    return {
        "output": Output(
            OutputMetadata("combined stdout & stderr", length=length),
            output,
            compression=compression,
        ),
    }


#-------------------------------------------------------------------------------

class ProgramRunning:

    def __init__(self, run_state, *, meta={}, times={}):
        self.run_state  = run_state
        self.meta       = meta
        self.times      = times


    def __repr__(self):
        return format_repr(self)



class ProgramUpdate:

    def __init__(self, *, meta={}, outputs={}):
        self.meta       = meta
        self.outputs    = outputs


    def __repr__(self):
        return format_repr(self)



# FIXME: Not an exception.
class ProgramError(RuntimeError):

    def __init__(self, message, *, meta={}, times={}, outputs={}):
        super().__init__(message)
        self.message    = message
        self.meta       = meta
        self.times      = times
        self.outputs    = outputs


    def __repr__(self):
        return format_repr(self)



class ProgramSuccess:

    def __init__(self, *, meta={}, times={}, outputs={}):
        self.meta       = meta
        self.times      = times
        self.outputs    = outputs


    def __repr__(self):
        return format_repr(self)



# FIXME: Not an exception.
class ProgramFailure(RuntimeError):

    def __init__(self, message, *, meta={}, times={}, outputs={}):
        self.message    = message
        self.meta       = meta
        self.times      = times
        self.outputs    = outputs


    def __repr__(self):
        return format_repr(self)



#-------------------------------------------------------------------------------

@dataclass
class Timeout:

    duration: float
    signal: str

    @classmethod
    def from_jso(cls, jso):
        with check_schema(jso) as pop:
            duration = pop("duration")
            signal = pop("signal", str, default="SIGTERM")
        return cls(duration=duration, signal=signal)


    def to_jso(self):
        return {
            "duration": self.duration,
            "signal": self.signal,
        }


    def bind(self, args):
        duration = parse_duration(template_expand(self.duration, args))
        signal = to_signal(template_expand(self.signal, args)).name
        return type(self)(duration=duration, signal=signal)



#-------------------------------------------------------------------------------

class Program(TypedJso):
    """
    Program base class.
    """

    TYPE_NAMES = TypedJso.TypeNames()

    def bind(self, args):
        """
        Returns a new program with parameters bound to `args`.
        """


    # FIXME: Find a better way to get run_id into logging without passing it in.

    async def start(self, run_id, cfg):
        """
        Starts the run.

        :deprecated:
          Implement `run()` instead.
        """


    def reconnect(self, run_id, run_state):
        """
        Reconnects to an already running run.

        :deprecated:
          Implement `connect()` instead.
        """


    async def signal(self, run_id, signum: str):
        """
        Sends a signal to the running program.

        :param run_id:
          The run ID; used for logging only.
        :param signum:
          Signal name or number.
        """


    @classmethod
    def from_jso(cls, jso):
        # Extend the default JSO typed resolution to accept a str or list.
        if isinstance(jso, str):
            from .agent import AgentShellProgram
            return AgentShellProgram(jso)
        elif isinstance(jso, list):
            from .agent import AgentProgram
            return AgentProgram(jso)
        else:
            return TypedJso.from_jso.__func__(cls, jso)


    async def run(self, run_id, cfg):
        """
        Runs the program.

        The default implementation is a facade for `start()`, for backward
        compatibility.  Subclasses should override this method.

        :param run_id:
          Used for logging only.
        :return:
          Async iterator that yields `Program*` objects.
        """
        # Starting.
        try:
            running, done = await self.start(run_id, cfg)
        except ProgramError as err:
            yield err
        else:
            assert isinstance(running, ProgramRunning)
            yield running

        # Running.
        try:
            success = await done
        except (ProgramError, ProgramFailure) as err:
            yield err
        else:
            assert isinstance(success, ProgramSuccess)
            yield success


    async def connect(self, run_id, run_state, cfg):
        """
        Connects to the running program specified by `run_state`.

        The default implementation is a facade for `reconnect()`, for backward
        compatibility.  Subclasses should override this method.

        :param run_id:
          Used for logging only.
        :return:
          Async iterator that yields `Program*` objects.
        """
        done = self.reconnect(run_id, run_state)
        try:
            success = await done
        except (ProgramError, ProgramFailure) as err:
            yield err
        else:
            assert isinstance(success, ProgramSuccess)
            yield success



#-------------------------------------------------------------------------------

class _InternalProgram(Program):
    """
    Program type for internal use.

    Not API.  Do not use in extension code.
    """

    def bind(self, args):
        pass


    async def start(self, run_id, apsis):
        pass


    def reconnect(self, run_id, run_state):
        pass


    async def signal(self, run_id, signum: str):
        pass



