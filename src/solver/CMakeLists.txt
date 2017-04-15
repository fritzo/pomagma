include_directories(${CMAKE_SOURCE_DIR}/include)

add_library(pomagma_solver SHARED
	syntax.cpp
	theory_solver.cpp
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

add_executable(syntax_test syntax_test.cpp)
set_source_files_properties(syntax_test.cpp COMPILE_FLAGS ${GTEST_FLAGS})
target_link_libraries(syntax_test ${POMAGMA_SOLVER_LIBS} gtest_main)
add_test(NAME solver_syntax COMMAND syntax_test)

add_executable(theory_solver_test theory_solver_test.cpp)
set_source_files_properties(theory_solver_test.cpp COMPILE_FLAGS ${GTEST_FLAGS})
target_link_libraries(theory_solver_test ${POMAGMA_SOLVER_LIBS} gtest_main)
add_test(NAME solver_theory_solver COMMAND theory_solver_test)

add_executable(solver_test solver_test.cpp)
set_source_files_properties(solver_test.cpp COMPILE_FLAGS ${GTEST_FLAGS})
target_link_libraries(solver_test ${POMAGMA_SOLVER_LIBS} gtest_main)
add_test(NAME solver_solver COMMAND solver_test)

add_executable(solve solve_main.cpp)
target_link_libraries(solve ${POMAGMA_SOLVER_LIBS})
