import contextlib
import ujson

from   .exc import SchemaError
from   .imp import import_fqname, get_type_fqname

#------------------------------------------------------------------------------

def to_array(obj):
    return obj if isinstance(obj, list) else [obj]


@contextlib.contextmanager
def no_unexpected_keys(jso):
    """
    On exit, checks that all JSO keys have been popped.

    :raise SchemaError:
      The JSO is not empty at the end of the context body.
    """
    original = dict(jso)
    yield jso
    if len(jso) > 0:
        keys = ", ".join( f'"{k}"' for k in jso )
        raise SchemaError(
            f"unexpected {keys} in structure:\n"
            + ujson.dumps(original, indent=2)
        )


#-------------------------------------------------------------------------------

class TypedJso:
    """
    Support for JSON de/serialization of subtypes.

    Mix in to the base class:

        class Base(TypedJso):

            TYPE_NAMES = TypedJso.TypeNames()


    In each concrete subtype:

        class Subtype(Base):

            @classmethod
            def from_jso(cls, jso):
                # deserialize...


            def to_jso(self):
                return {
                    **super().to_jso(),
                    # serialize...
                }

    The concrete subtype is encoded as a "type" field in the JSO, using the 
    fully-qualified type name.  Provide shorter type aliases with,

        Base.TYPE_NAMES.set(Subtype, "short_name")

    """

    class TypeNames:

        def __init__(self):
            self.__by_name = {}
            self.__by_type = {}


        def set(self, type, name):
            self.__by_name[name] = type
            self.__by_type[type] = name


        def get_type(self, name):
            try:
                return self.__by_name[name]
            except KeyError:
                return import_fqname(name)


        def get_name(self, type):
            try:
                return self.__by_type[type]
            except KeyError:
                return get_type_fqname(type)



    @classmethod
    def from_jso(cls, jso):
        with no_unexpected_keys(jso):
            try:
                name = jso.pop("type")

            except KeyError:
                # No type field specified.
                raise SchemaError("missing type")

            else:
                type = cls.TYPE_NAMES.get_type(name)
                if not issubclass(type, cls):
                    raise SchemaError(f"type {type} not a {cls}")

            return type.from_jso(jso)


    def to_jso(self):
        return {
            "type": self.TYPE_NAMES.get_name(type(self)),
        }


    def __eq__(self, other):
        return type(other) == type(self) and other.to_jso() == self.to_jso()



