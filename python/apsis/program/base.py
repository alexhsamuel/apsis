from   apsis.lib.api import decompress
from   apsis.lib.json import TypedJso

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

    def __init__(self, metadata: OutputMetadata, data, compression=None):
        """
        :param metadata:
          Information about the data.
        :param data:
          The data bytes; these may be compressed.
        :pamam compression:
          The compresison type, or `None` for uncompressed.
        """
        self.metadata       = metadata
        self.data           = data
        self.compression    = compression


    def get_uncompressed_data(self) -> bytes:
        """
        Returns the output data, decompressing if necessary.
        """
        return decompress(self.data, self.compression)



def program_outputs(output, *, length=None, compression=None):
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



class ProgramError(RuntimeError):

    def __init__(self, message, *, meta={}, times={}, outputs={}):
        super().__init__(message)
        self.message    = message
        self.meta       = meta
        self.times      = times
        self.outputs    = outputs



class ProgramSuccess:

    def __init__(self, *, meta={}, times={}, outputs={}):
        self.meta       = meta
        self.times      = times
        self.outputs    = outputs



class ProgramFailure(RuntimeError):

    def __init__(self, message, *, meta={}, times={}, outputs={}):
        self.message    = message
        self.meta       = meta
        self.times      = times
        self.outputs    = outputs



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

        Updates `run` in place.

        :param run_id:
          The run ID; used for logging only.
        :param cfg:
          The global config.
        :raise ProgramError:
          The program failed to start.
        :return:
          `running, done`, where `running` is a `ProgramRunning` instance and
          `done` is a coroutine or future that returns `ProgramSuccess` when the
          program is complete.
        """


    def reconnect(self, run_id, run_state):
        """
        Reconnects to an already running run.

        :param run_id:
          The run ID; used for logging only.
        :param run_state:
          State information for the running program.
        :return:
          A coroutine or future for the program completion, as `start`.
        """


    async def signal(self, run_id, signum: str):
        """
        Sends a signal to the running program.

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



