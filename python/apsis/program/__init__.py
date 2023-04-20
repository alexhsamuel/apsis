from   .base import (
    Program, Output, OutputMetadata,
    ProgramRunning, ProgramError, ProgramSuccess, ProgramFailure,
)
from   .noop import NoOpProgram
from   .agent import AgentProgram, AgentShellProgram
from   .process import ProcessProgram, ShellCommandProgram

#-------------------------------------------------------------------------------

Program.TYPE_NAMES.set(NoOpProgram, "no-op")
Program.TYPE_NAMES.set(AgentProgram, "program")
Program.TYPE_NAMES.set(AgentShellProgram, "shell")

