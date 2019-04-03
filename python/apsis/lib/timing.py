import time

#-------------------------------------------------------------------------------

class Timer:

    def __init__(self, name="timer", print=None):
        self.__name = str(name)
        self.__print = print
        self.__start = None
        self.__elapsed = None


    def __enter__(self):
        self.__start = time.perf_counter()
        return self


    def __exit__(self, exc_type, exc, exc_tb):
        self.__elapsed = time.perf_counter() - self.__start
        if self.__print is not None:
            self.__print(f"{self.__name} elapsed: {self.__elapsed:.3f} s")


    @property
    def elapsed(self):
        return (
            time.perf_counter() - self.__start if self.__elapsed is None
            else self.__elapsed
        )



