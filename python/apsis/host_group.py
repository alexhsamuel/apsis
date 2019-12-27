"""
Designation of host(s) to run on.
"""

import random

from   .lib.json import TypedJso
from   .runs import template_expand

#-------------------------------------------------------------------------------

class HostGroup(TypedJso):

    TYPE_NAMES = TypedJso.TypeNames()

    def __init__(self, hosts):
        self.__hosts = tuple(hosts)
        assert all( isinstance(h, str) for h in self.__hosts )


    @property
    def hosts(self):
        return self.__hosts


    def bind(self, args):
        hosts = tuple( template_expand(a, args) for a in self.__hosts )
        return type(self)(hosts)



class RoundRobinHostGroup(HostGroup):
    """
    A round-robin cycle of hosts.
    """

    def __init__(self, hosts):
        super().__init__(hosts)
        self.__index = 0


    @classmethod
    def from_jso(cls, jso):
        return cls(jso.pop("hosts"))


    def to_jso(self):
        return {
            **super().to_jso(),
            "hosts": self.hosts,
        }


    def choose(self):
        host = self.hosts[self.__index]
        self.__index = (self.__index + 1) % len(self.hosts)
        return host




class RandomHostGroup(HostGroup):
    """
    A list of hosts to choose from at random with replacement.
    """

    @classmethod
    def from_jso(cls, jso):
        return cls(jso.pop("hosts"))


    def to_jso(self):
        return {
            **super().to_jso(),
            "hosts": self.hosts,
        }


    def choose(self):
        return random.choice(self.hosts)



# Aliases.
HostGroup.TYPE_NAMES.set(RoundRobinHostGroup, "round-robin")
HostGroup.TYPE_NAMES.set(RandomHostGroup, "random")

