
class Job:

    def __init__(self, id, command):
        self.__id = id
        self.__command = str(command)


    @property
    def id(self):
        return self.__id


    @property
    def command(self):
        return self.__command



