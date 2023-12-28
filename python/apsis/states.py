import enum

from   apsis.lib import py

#-------------------------------------------------------------------------------

State = enum.Enum(
    "State",
    (
        "new",
        "scheduled",
        "waiting",
        "starting",
        "running",
        "success",
        "failure",
        "error",
        "skipped",
    )
)

ALL_STATES = frozenset(State)
FINISHED = frozenset((State.success, State.failure, State.error, State.skipped))

# State model.  Allowed transitions _to_ each state.
TRANSITIONS = {
    State.new       : set(),
    State.scheduled : {State.new},
    State.waiting   : {State.new, State.scheduled},
    State.starting  : {State.scheduled, State.waiting},
    State.running   : {State.starting},
    State.error     : {State.new, State.scheduled, State.waiting, State.starting, State.running, State.skipped},
    State.success   : {State.running},
    State.failure   : {State.running},
    State.skipped   : {State.new, State.scheduled, State.waiting},
}

def states_from_jso(jso):
    return frozenset( State[s] for s in py.tupleize(jso) )


def states_to_jso(states):
    states = frozenset(states)
    return (
        None if states == ALL_STATES
        else [ s.name for s in states ]
    )


def reachable(state):
    """
    Returns the set of states reachable from `state` by zero or more
    transitions.
    """
    reachable = {state}
    while True:
        # Find immediate successors.
        succ = {
            s
            for s, pred in TRANSITIONS.items()
            if any( r in pred for r in reachable )
        }
        # If there are no new successors, stop.
        if len(succ - reachable) == 0:
            return reachable
        else:
            reachable |= succ


