import random
import sys

#-------------------------------------------------------------------------------

class Instance:

    def __init__(self, job):
        self.__job = job
        self.__id = random.randint(0, sys.maxsize)


    @property
    def job(self):
        return self.__job


    @property
    def id(self):
        return self.__id




