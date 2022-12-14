import pytest

import apsis.agent.client

#-------------------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def agent_state_dir():
    with apsis.agent.client.test_state_dir():
        yield


