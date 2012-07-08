
current_target: all

all: libpomagma.a libpomagma.so test

#----( params )----------------------------------------------------------------

PLATFORM := $(shell uname)
#PLATFORM = Linux
#PLATFORM = cygwin
#PLATFORM = Darwin

# this only applies when debugging
DEBUG_LEVEL = 3

#----( compile flags )---------------------------------------------------------

CXX = g++
CC = g++
LEX = flex
YACC = bison

WARNINGS = -Wall -Woverloaded-virtual -Wsign-promo -Wundef -Wpointer-arith -Wcast-qual -Wcast-align -Wno-deprecated

OPTIM = -O2 -pipe
#OPTIM = -O2 -funswitch-loops -fomit-frame-pointer -pipe -march

CPPFLAGS = -I. -Wstrict-aliasing --std=c++0x -DDEBUG_LEVEL=$(DEBUG_LEVEL)
CXXFLAGS = -fno-strict-aliasing $(OPTIM) $(WARNINGS) -fPIC -ggdb
LDFLAGS = $(OPTIM) -L. -lpomagma

#platform-dependent flags
ifeq ($(PLATFORM), Linux)
	CPPFLAGS += -pthread
	LDFLAGS += -pthread -rdynamic
	GL = $(GL_LINUX)
endif
ifeq ($(PLATFORM), Darwin)
	CPPFLAGS += -DMAC_HACKS
	GL = $(GL_MAC)
endif

#----( build rules )----------------------------------------------------------

#.SUFFIXES:

%.o: %.cpp
	@echo compiling $@
	@$(CXX) $(CPPFLAGS) $(CXXFLAGS) -c $< -o $@
%.so:
	@echo linking $@
	@$(CXX) -shared $^ -o $@
%.a:
	@echo archiving $@
	@ar rcs $@ $^
%_test:
	@echo linking $@
	@$(CXX) $(CXXFLAGS) $^ $(LDFLAGS) -o $@

#----( modules )--------------------------------------------------------------

ALL_O = dense_sym_fun.o dense_bin_fun.o sparse_bin_fun.o dense_bin_rel.o dense_set.o aligned_alloc.o util.o

libpomagma.a: $(ALL_O)

libpomagma.so: $(ALL_O)

#----( testing )--------------------------------------------------------------

binary_relation_test: binary_relation_test.o

dense_sym_fun_test: dense_sym_fun_test.o

TESTS = binary_relation_test dense_sym_fun_test

# TODO automate this
test: $(TESTS)
	@echo "" > temp.log
	@for t in $(TESTS); do \
		echo running $$t; \
		./$$t; \
	done

#----( utilities )------------------------------------------------------------

clean: FORCE
	rm -rf $(TESTS)
	rm -rf *.o
	rm -rf *.so
	rm -rf *.a

depend:
	@makedepend -D__GNUG__ -Y *.cpp -fcpp.depend 2> makedepend.log
	@! grep -i error makedepend.log

include cpp.depend

FORCE:

