from   .base import (
    Program, Output, OutputMetadata,
    ProgramRunning, ProgramError, ProgramSuccess, ProgramFailure,
)

from   .agent import AgentProgram, AgentShellProgram
from   .noop import NoOpProgram
from   .process import ProcessProgram, ShellCommandProgram
from   .procstar.ws import ProcstarProgram

#-------------------------------------------------------------------------------

Program.TYPE_NAMES.set(NoOpProgram, "no-op")
Program.TYPE_NAMES.set(AgentProgram, "program")
Program.TYPE_NAMES.set(AgentShellProgram, "shell")
Program.TYPE_NAMES.set(ProcstarProgram, "procstar")

