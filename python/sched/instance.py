import random
import sys

from   .job import Job

#-------------------------------------------------------------------------------

class Instance:

    def __init__(self, job, id=None):
        self.__job = job
        self.__id = random.randint(0, sys.maxsize) if id is None else int(id)


    @property
    def job(self):
        return self.__job


    @property
    def id(self):
        return self.__id


    def to_jso(self):
        return {
            "job": self.__job.to_jso(),
            "id": self.__id,
        }


    @staticmethod
    def from_jso(class_, jso):
        return class_(Job.from_iso(jso["job"]), jso["id"])



