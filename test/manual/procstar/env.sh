export TZ=UTC

PROCSTAR_PATH=$(python -c 'from procstar.testing import get_procstar_path; print(get_procstar_path());')
test -f $PROCSTAR_PATH || (echo "missing $PROCSTAR_PATH" >&2; exit 1)

export PROCSTAR_AGENT_CERT=$(python -c 'from procstar.testing import TLS_CERT_PATH; print(TLS_CERT_PATH);')
test -f $PROCSTAR_AGENT_CERT || (echo "missing $PROCSTAR_AGENT_CERT" >&2; exit 1)

export PROCSTAR_AGENT_TOKEN=foobar

export PROCSTAR_AGENT_HOST=localhost

printenv | grep PROCSTAR | sort
