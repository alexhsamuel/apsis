import logging
import os
import pytest
import shutil
import tempfile

#-------------------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def agent_state_dir():
    # This module is used in testing only.  Set the agent state dir to a unique,
    # private path.
    state_dir = tempfile.mkdtemp(prefix="apsis-agent-test-")
    logging.info(f"agent state dir: {state_dir}")
    os.environ["APSIS_AGENT_STATE_DIR"] = state_dir

    yield

    # Clean up the state dir.
    logging.info(f"cleaning up agent state dir: {state_dir}")
    del os.environ["APSIS_AGENT_STATE_DIR"]
    shutil.rmtree(state_dir)


