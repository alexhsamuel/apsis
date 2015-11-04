include ../Makefile.local

SHELL	    	= /bin/bash

CPPFLAGS    	= -I $(shell pwd)
CXXFLAGS    	= -Werror -Wall -Wextra -g

SOURCES		= $(wildcard *.cc) $(wildcard cron/*.cc)
DEPS	    	= $(SOURCES:.cc=.dd)
OBJS	    	= $(SOURCES:.cc=.o)
LIB 	    	= libsched.a

#-------------------------------------------------------------------------------

.PHONY: 		all clean doc

all:	    	    	$(LIB)

$(LIB):			$(OBJS)
	$(AR) r $@ $^
	$(AR) s $@

# The generated .dd file gives the basename of the object file as the target,
# not the full relative path.  Fix this.  Also add the dependecy file as a
# target of the same includes.
$(DEPS): %.dd: 		%.cc
	@echo "generating $@"; set -e; \
	base=`basename $*`; \
	$(CXX) -MM $(CPPFLAGS) $< \
	  | sed "s,$$base\.o[ :]*,$*.o $@ : ,g" > $@

clean:
	rm -f $(DEPS) $(OBJS) $(LIB)

doc:
	doxygen 

#-------------------------------------------------------------------------------

include $(DEPS)

