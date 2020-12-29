import contextlib
import ujson

from   .exc import SchemaError
from   .imp import import_fqname, get_type_fqname

#------------------------------------------------------------------------------

NO_DEFAULT = object()

def to_array(obj):
    return obj if isinstance(obj, list) else [obj]


@contextlib.contextmanager
def check_schema(jso):
    """
    Wraps a JSO dict in a `pop` function.  On exit, checks for no remaining
    keys.
    """
    copy = dict(jso)

    def pop(key, type=None, default=NO_DEFAULT):
        try:
            value = copy.pop(key)
        except KeyError:
            if default is NO_DEFAULT:
                raise SchemaError(f"missing key: {key}") from None
            else:
                value = default
        else:
            if type is not None:
                value = type(value)
        return value

    try:
        yield pop
    except Exception as exc:
        raise SchemaError(str(exc))

    if len(copy) > 0:
        raise SchemaError(f"unexpected keys: {' '.join(copy)}")


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



