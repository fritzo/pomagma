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

function(add_unit_test T)
	pomagma_add_executable(${T}_test ${T}_test.cpp)
	set_source_files_properties(${T}_test.cpp COMPILE_FLAGS ${GTEST_FLAGS})
	target_link_libraries(${T}_test
	       	${POMAGMA_SOLVER_LIBS}
	       	pomagma_gtest_main
	)
	add_test(NAME solver_${T} COMMAND ${T}_test)
endfunction()

add_unit_test(syntax)
add_unit_test(theory_solver)
add_unit_test(solver)

pomagma_add_executable(solve solve_main.cpp)
target_link_libraries(solve ${POMAGMA_SOLVER_LIBS})
