import logging
from   pathlib import Path
import pickle

#-------------------------------------------------------------------------------

class InstanceDB:

    def __init__(self, path):
        self.__path = Path(path)
        if self.__path.exists():
            with self.__path.open("rb") as file:
                self.__instances = pickle.load(file)
        else:
            logging.warning(
                "db {} doesn't exist; creating new".format(self.__path))
            self.__instances = {}


    def create_instance(self, instance):
        if instance.id in self.__instances:
            raise ValueError(
                "instance {} already exists".format(instance.id))

        self.__instances[instance.id] = None
        self.__write()


    def log(self, instance, msg):
        # FIXME
        pass


    def set_result(self, instance, result):
        if instance.id not in self.__instances:
            raise LookupError("instance {} does not exist".format(instance.id))

        self.__instances[instance.id] = result
        self.__write()



    def get_result(self, instance):
        """
        Returns `None` if the instance has not run.
        """
        try:
            return self.__instances[instance.id]
        except KeyError:
            raise LookupError("instance {} does not exist".format(instance.id))


    def __write(self):
        with self.__path.open("wb") as file:
            pickle.dump(self.__instances, file)



