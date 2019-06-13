from   apsis.lib.json import Typed, no_unexpected_keys
from   .dependency import Dependency
from   .max_running import MaxRunning

#-------------------------------------------------------------------------------

TYPES = Typed({
    "dependency"        : Dependency,
    "max_running"       : MaxRunning,
})

def cond_from_jso(jso):
    with no_unexpected_keys(jso):
        return TYPES.from_jso(jso)


cond_to_jso = TYPES.to_jso

