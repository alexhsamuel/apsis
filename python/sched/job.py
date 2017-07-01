
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


    def to_jso(self):
        return {
            "id": self.__id,
            "command": self.__command,
        }


    @staticmethod
    def from_jso(class_, jso):
        return class_(jso["id"], jso["command"])




