include ../Makefile.local

CXXFLAGS    	= -Wall -Wextra -g
CPPFLAGS	= -I../src

LDLIBS		= ../src/libsched.a

TESTS		= action \
		  action1 \
		  date0 \
		  event0 \
		  fd_handler0 \
		  fd_handler1 \
	 	  filename1 \
		  filename2 \
		  json0 \
		  json1 \
		  json2 \
		  printable \
		  program0 \
		  program1 \
		  summarize-limits \
		  tzfile0 \
	          to_string 

CTESTS		= tzfile

.PHONY:			all clean

all:			$(TESTS)

$(TESTS): %:		%.o $(LDLIBS)
	$(CXX) $(CXXFLAGS) $(LDFLAGS) $^ -o $@

$(CTESTS): %: 		%.o
	$(CC) $(CXXFLAGS) $(LDFLAGS) $^ -o $@

clean:
	rm -f *.dd *.o $(TESTS)

