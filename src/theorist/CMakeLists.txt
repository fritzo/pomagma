
include_directories(${CMAKE_SOURCE_DIR}/)

add_library(pomagma_theorist SHARED
	hypothesize.cpp
	conjecture_equal.cpp
	conjecture_diverge.cpp
	)
set(POMAGMA_THEORIST_LIBS
	pomagma_theorist
	pomagma_macrostructure
	pomagma_platform_sequential
	pomagma_language
	${POMAGMA_SEQUENTIAL_LIBS})

add_executable(conjecture_equal conjecture_equal_main.cpp)
target_link_libraries(conjecture_equal ${POMAGMA_THEORIST_LIBS})

add_executable(conjecture_diverge conjecture_diverge_main.cpp)
target_link_libraries(conjecture_diverge ${POMAGMA_THEORIST_LIBS})
