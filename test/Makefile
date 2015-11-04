include ../Makefile.local

CXXFLAGS       += -g -Werror -Wall -Wextra

GTEST_DIR   	= ./gtest
CPPFLAGS       += -I$(GTEST_DIR)/include
GTEST_HEADERS 	= $(GTEST_DIR)/include/gtest/*.h \
                  $(GTEST_DIR)/include/gtest/internal/*.h
LDLIBS	       += $(GTEST_DIR)/gtest_main.a \
		  -lpthread

CPPFLAGS       += -I../src
LIBS	    	= ../src/libsched.a

SOURCES	    	= $(wildcard *.cc)
DEPS	    	= $(SOURCES:%.cc=%.dd)
OBJS    	= $(SOURCES:%.cc=%.o)
BINS    	= $(SOURCES:%.cc=%)
OKS 	    	= $(SOURCES:%.cc=%.ok)

#-------------------------------------------------------------------------------

.PHONY:	    	    	all clean test run

all: 	    	    	test

clean:
	    	    	rm -f $(OBJS) $(BINS) $(DEPS) $(OKS)

run:			$(BINS)
	@fail=0; for test in $^; do echo Running $$test; $$test || fail=1; echo; echo; done; exit $$fail

test:	    	    	$(OKS)

$(DEPS): %.dd: 		%.cc
	@echo "generating $@"; set -e; \
	$(CXX) -MM $(CPPFLAGS) $< | sed 's,\($*\)\.o[ :]*,\1.o $@ : ,g' > $@

$(OBJS): %.o:   	%.cc
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -c $< -o $@

$(BINS): %: 		%.o $(LIBS)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) $< $(LIBS) $(LDLIBS) -o $@

$(OKS): %.ok:    	%
	@rm -f $@
	./$< && touch $@

#-------------------------------------------------------------------------------

include $(DEPS)

