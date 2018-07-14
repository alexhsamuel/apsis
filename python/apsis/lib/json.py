from   .exc import SchemaError

#------------------------------------------------------------------------------

class Typed:

    def __init__(self, types={}, *, default=None):
        """
        Creates a type mapping for JSO serialization.

        Each type must have a `from_jso` static/class method.

        :param types:
          Mapping from type name to type.  
        :param default_type:
          The type to use if `jso` does not have a "type" field; `None` for no
          default.
        """
        self.__default = default
        self.__by_name = {}
        self.__by_type = {}
        self.add(**types)


    def add(self, **types):
        """
        Registers one or more types, by name.

        Each type must have a `from_jso` static/class method.
        """
        for name, type in types.items():
            self.__by_name[name] = type
            self.__by_type[type] = name


    def from_jso(self, jso):
        """
        Deserializes an object from `jso`, dispatching on type name.

        The type is determined from the "type" field in `jso`.
        """
        try:
            name = jso["type"]

        except KeyError:
            # No type field specified.
            if self.__default is None:
                raise SchemaError("missing type")
            else:
                type = self.__default

        else:
            try:
                type = self.__by_name[name]
            except KeyError:
                raise SchemaError(f"unknown type: {name}")

        return type.from_jso(jso)


    def to_jso(self, obj):
        try:
            name = self.__by_type[type(obj)]
        except KeyError:
            raise TypeError(f"unregistered type: {type(obj)}")

        return {
            **obj.to_jso(),
            "type": name,
        }



