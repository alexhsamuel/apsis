from   .py import format_ctor, iterize

class NetAddress:

    def __init__(self, host, port):
        self.host = str(host)
        self.port = int(port)


    def __repr__(self):
        return format_ctor(self.host, self.port)


    def __str__(self):
        return f"{self.host}:{self.port}"


    def __iter__(self):
        return iter((self.host, self.port))


    @staticmethod
    def split(addr):
        """
        Interprets `addr` as a `host, port` pair or a `"host:port"` string.

        Does not convert `port` to integer.
        """
        try:
            host, port = iterize(addr)
        except (TypeError, ValueError):
            pass
        else:
            return host, port

        try:
            host, port = str(addr).split(":", 1)
        except ValueError:
            pass
        else:
            return host, port

        raise ValueError("can't split net address: {addr!r}")


    @classmethod
    def convert(cls, addr):
        host, port = cls.split(addr)
        return cls(host, port)


    def to_jso(self):
        return (self.host, self.port)


    @classmethod
    def from_jso(cls, jso):
        host, port = cls.split(jso)
        return cls(host, port)



