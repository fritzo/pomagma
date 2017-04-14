include_directories(${CMAKE_SOURCE_DIR}/include)

add_library(pomagma_solver SHARED
	structure.cpp
	solver.cpp
)
target_link_libraries(pomagma_solver
	${POMAGMA_IO_LIBS}
	${POMAGMA_UTIL_LIBS}
)
set(POMAGMA_SOLVER_LIBS
	pomagma_solver
	${POMAGMA_IO_LIBS}
	${POMAGMA_UTIL_LIBS}
)

add_executable(structure_test structure_test.cpp)
set_source_files_properties(structure_test.cpp COMPILE_FLAGS ${GTEST_FLAGS})
target_link_libraries(structure_test ${POMAGMA_SOLVER_LIBS} gtest_main)
add_test(NAME solver_structure COMMAND structure_test)

add_executable(solver_test solver_test.cpp)
set_source_files_properties(solver_test.cpp COMPILE_FLAGS ${GTEST_FLAGS})
target_link_libraries(solver_test ${POMAGMA_SOLVER_LIBS} gtest_main)
add_test(NAME solver_solver COMMAND solver_test)

add_executable(solve solve_main.cpp)
target_link_libraries(solve ${POMAGMA_SOLVER_LIBS})
