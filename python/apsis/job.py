from    aslib.py import format_ctor

#-------------------------------------------------------------------------------

class Job:

    def __init__(self, id, schedule, program):
        self.__id       = str(id)
        self.__schedule = schedule
        self.__program  = program


    @property
    def id(self):
        return self.__id


    @property
    def schedule(self):
        return self.__schedule


    @property
    def program(self):
        return self.__program



class Instance:

    def __init__(self, id, job, time):
        self.__id       = id
        self.__job      = job
        self.__time     = time


    def __repr__(self):
        return format_ctor(self, self.__id, self.__job, self.__time)


    @property
    def id(self):
        return self.__id


    @property
    def job(self):
        return self.__job


    @property
    def time(self):
        return self.__time



class Run:

    def __init__(self, id, inst):
        self.__id   = id
        self.__inst = inst


    @property
    def id(self):
        return self.__id


    @property
    def inst(self):
        return self.__inst



