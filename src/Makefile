
current_target: all

all: test

#----( params )----------------------------------------------------------------

PLATFORM := $(shell uname)
#PLATFORM = Linux
#PLATFORM = cygwin
#PLATFORM = Darwin

# this only applies when debugging
DEBUG_LEVEL = 3
OPTIM_LEVEL = 1

#----( compile flags )---------------------------------------------------------

CXX = g++
CC = g++
LEX = flex
YACC = bison

WARNINGS = -Wall -Woverloaded-virtual -Wsign-promo -Wundef -Wpointer-arith -Wcast-qual -Wcast-align -Wno-deprecated

OPTIM = -O2 -pipe
#OPTIM = -O2 -funswitch-loops -fomit-frame-pointer -pipe -march

# opengl stuff
GL_LINUX = -lglut -lGLU -lGL
GL_MAC = -framework OpenGL -framework Glut
GL_CYGWIN = -lglut32 -lglu32 -lopengl32

#LFLAGS = -d #flex is called manually below
YFLAGS = -d
CPPFLAGS = -I. -Wstrict-aliasing --std=c++0x -DDEBUG_LEVEL=$(DEBUG_LEVEL)
CXXFLAGS = -fno-strict-aliasing $(OPTIM) $(WARNINGS) -ggdb
LDFLAGS = $(OPTIM)

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

.SUFFIXES:

%.o: %.cpp
	@echo compiling $@
	@$(CXX) $(CPPFLAGS) $(CXXFLAGS) -c $< -o $@
%_test:
	@echo linking $@
	@$(CXX) $(CXXFLAGS) $^ $(LDFLAGS) -o $@

#requires_rtti_and_exceptions.o: requires_rtti_and_exceptions.C
#	@echo compiling $<
#	@$(CXX) $(CPPFLAGS) $(CXXFLAGS) -frtti -fexceptions -c $< -o $@

#----( modules )--------------------------------------------------------------

ALL_O = dense_sym_fun.o dense_bin_fun.o sparse_bin_fun.o dense_bin_rel.o dense_set.o aligned_alloc.o util.o

#----( testing )--------------------------------------------------------------

binary_relation_test: binary_relation_test.o $(ALL_O) aligned_alloc.o util.o

dense_sym_fun_test: dense_sym_fun_test.o $(ALL_O)

TESTS = binary_relation_test dense_sym_fun_test

# TODO automate this
test: $(TESTS)
	@echo "" > temp.log
	@for t in $(TESTS); do \
		echo running $$t; \
		./$$t; \
	done

#----( utilities )------------------------------------------------------------

clean: lclean oclean FORCE
	rm -rf $(TESTS)
	rm -rf *.o

depend:
	@makedepend -D__GNUG__ -Y *.cpp -fcpp.depend 2> makedepend.log
	@! grep -i error makedepend.log

include cpp.depend

FORCE:

