import pytest

from   apsis.program import Program, ProgramSuccess

#-------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_process_program():
    program = Program.from_jso({
        "type": "apsis.program.process.ProcessProgram",
        "argv": ["/usr/bin/echo", "Hello, {{ name }}!"],
    })
    program = program.bind({"name": "world"})

    running = program.run("testrun", cfg={})
    async for update in running.updates:
        pass

    assert isinstance(update, ProgramSuccess)
    assert update.meta["return_code"] == 0
    output = update.outputs["output"]
    assert output.data == b"Hello, world!\n"


@pytest.mark.asyncio
async def test_shell_command_program():
    program = Program.from_jso({
        "type": "apsis.program.process.ShellCommandProgram",
        "command": "echo 'Hello, {{ name }}!'",
    })
    program = program.bind({"name": "world"})

    running = program.run("testrun", cfg={})
    async for update in running.updates:
        pass

    assert isinstance(update, ProgramSuccess)
    assert update.meta["return_code"] == 0
    output = update.outputs["output"]
    assert output.data == b"Hello, world!\n"


