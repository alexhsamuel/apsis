from   .lib import json, py

#-------------------------------------------------------------------------------

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
                pop("by", default={}),
            )


    def to_jso(self):
        return {
            "constant": self.constant,
            "by": self.parametrized,
        }


    def __repr__(self):
        return py.format_ctor(self, self.constant, self.parametrized)


    def __eq__(self, other):
        return (
                other.constant == self.constant
            and other.parametrized == self.parametrized
        )


    def get(self, name, args, default):
        for param, val in args.items():
            try:
                return self.parametrized[param][str(val)][name]
            except KeyError:
                pass

        try:
            return self.constant[name]
        except KeyError:
            pass

        return default


    def get_for_args(self, args):
        result = dict(self.constant)
        for param, val in args.items():
            try:
                param_args = self.parametrized[param][str(val)]
            except KeyError:
                pass
            else:
                result.update(param_args)
        return result



