from   .lib import json, py

class Definitions:

    def __init__(self, constant={}, parametrized={}):
        self.constant = { str(k): v for k, v in constant.items() }
        self.parametrized = {
            str(p): {
                str(a): {
                    str(d): dv
                    for d, dv in av.items()
                }
                for a, av in pv.items()
            }
            for p, pv in parametrized.items()
        }


    @classmethod
    def from_jso(cls, jso):
        with json.check_schema(jso) as pop:
            return cls(
                pop("constant", default={}),
                pop("parametrized", default={}),
            )


    def to_jso(self):
        return {
            "constant": self.constant,
            "parametrized": self.parametrized,
        }


    def __repr__(self):
        return py.format_ctor(self, self.constants, self.parametrized)


    def __eq__(self, other):
        return (
                other.constant == self.constant
            and other.parametrized == self.parametrized
        )


