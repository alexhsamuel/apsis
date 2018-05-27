from   . import py
import collections

__all__ = (
    "Interval",
    "to_interval",
)

#-------------------------------------------------------------------------------

class Interval:

    def __init__(self, start, stop):
        assert start <= stop
        self.__start = start
        self.__stop = stop


    def __repr__(self):
        return py.ctor(self, self.__start, self.__stop)


    def __str__(self):
        return "[{}, {})".format(self.__start, self.__stop)


    def __iter__(self):
        return iter((self.__start, self.__stop))


    def __contains__(self, value):
        return self.__start <= value < self.__stop


    @property
    def start(self):
        return self.__start


    @start.setter
    def set_start(self, start):
        assert start <= self.__stop
        self.__start = start


    @property
    def stop(self):
        return self.__stop


    @stop.setter
    def set_stop(self, stop):
        assert self.__start <= stop
        self.__stop = stop

    


def to_interval(obj):
    try:
        start = obj.start
        stop = obj.stop
    except AttributeError:
        pass
    else:
        return interval(start, stop)

    try:
        start, stop = obj
    except (TypeError, ValueError):
        pass
    else:
        return interval(start, stop)

    raise TypeError("not an interval: {!r}".format(obj))


#-------------------------------------------------------------------------------

def format_time(time):
    # FIXME: For now, assume 1 s resolution.
    return format(time, "%Y-%m-%d %H:%M:%S")


