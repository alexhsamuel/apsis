CXX	       := $(CXX) -std=c++0x
CXXFLAGS    	= -Wall -g
CPPFLAGS	= -I..

LDLIBS		= ../libsched.a

#-------------------------------------------------------------------------------

.PHONY: 		all clean

all:	    	    	run

run:			run.o $(LDLIBS)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) $^ -o $@

clean:
	rm -f *.o run

