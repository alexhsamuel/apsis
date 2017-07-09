CXX	       := $(CXX) -std=c++11
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

