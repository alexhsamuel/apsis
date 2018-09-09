from   pathlib import Path

#-------------------------------------------------------------------------------

DEFAULT_PORT = 5100

_SSL_DIR    = Path(__file__).parent
SSL_CERT    = _SSL_DIR / "agent.cert"
SSL_KEY     = _SSL_DIR / "agent.key"

