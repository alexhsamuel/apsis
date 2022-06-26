class ConditionError(RuntimeError):
    """
    An error in specification of a condition.
    """


class TimeoutWaiting(RuntimeError):
    """
    A run timed out while waiting on conditions.
    """


