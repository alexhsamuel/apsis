
class Instance:

    def __init__(self, job, id):
        self.__job = job
        self.__id = id


    @property
    def job(self):
        return self.__job


    @property
    def id(self):
        return self.__id



