from   apsis.lib.json import TypedJso
from   ora import Time

#-------------------------------------------------------------------------------

class Schedule(TypedJso):

    TYPE_NAMES = TypedJso.TypeNames()

    def __init__(self, *, enabled=True):
        self.enabled = bool(enabled)


    def __call__(self, start: Time):
        raise NotImplementedError



