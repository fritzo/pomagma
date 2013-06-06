
include_directories(${CMAKE_SOURCE_DIR}/)

add_library(pomagma_theorist SHARED
	hypothesize.cpp
	conjecture.cpp
	)
set(POMAGMA_THEORIST_LIBS
	pomagma_theorist
	pomagma_macrostructure
	pomagma_platform_sequential
	${POMAGMA_SEQUENTIAL_LIBS})

add_executable(conjecture conjecture_main.cpp)
target_link_libraries(conjecture ${POMAGMA_THEORIST_LIBS})

