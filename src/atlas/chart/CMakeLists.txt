include_directories(${CMAKE_SOURCE_DIR}/include)

add_library(pomagma_chart SHARED
	carrier.cpp
	base_bin_rel.cpp
	unary_relation.cpp
	binary_relation.cpp
	nullary_function.cpp
	injective_function.cpp
	binary_function.cpp
	symmetric_function.cpp
	sampler.cpp
	structure.cpp
	scheduler.cpp
	vm.cpp
)

add_library(pomagma_chart_dummy SHARED dummy.theory.cpp)
set(POMAGMA_CHART_TEST_LIBS ${POMAGMA_CHART_LIBS} pomagma_chart_dummy)

add_executable(chart_carrier_test carrier_test.cpp)
target_link_libraries(chart_carrier_test ${POMAGMA_CHART_TEST_LIBS})
add_test(NAME chart_carrier COMMAND chart_carrier_test)

add_executable(chart_unary_relation_test unary_relation_test.cpp)
target_link_libraries(chart_unary_relation_test ${POMAGMA_CHART_TEST_LIBS})
add_test(NAME chart_unary_relation COMMAND chart_unary_relation_test)

add_executable(chart_binary_relation_test binary_relation_test.cpp)
target_link_libraries(chart_binary_relation_test ${POMAGMA_CHART_TEST_LIBS})
add_test(NAME chart_binary_relation COMMAND chart_binary_relation_test)

add_executable(chart_nullary_function_test nullary_function_test.cpp)
target_link_libraries(chart_nullary_function_test ${POMAGMA_CHART_TEST_LIBS})
add_test(NAME chart_nullary_function COMMAND chart_nullary_function_test)

add_executable(chart_injective_function_test injective_function_test.cpp)
target_link_libraries(chart_injective_function_test ${POMAGMA_CHART_TEST_LIBS})
add_test(NAME chart_injective_function COMMAND chart_injective_function_test)

add_executable(chart_binary_function_test binary_function_test.cpp)
target_link_libraries(chart_binary_function_test ${POMAGMA_CHART_TEST_LIBS})
add_test(NAME chart_binary_function COMMAND chart_binary_function_test)

add_executable(chart_symmetric_function_test symmetric_function_test.cpp)
target_link_libraries(chart_symmetric_function_test ${POMAGMA_CHART_TEST_LIBS})
add_test(NAME chart_symmetric_function COMMAND chart_symmetric_function_test)

add_executable(chart_scheduler_test scheduler_test.cpp)
target_link_libraries(chart_scheduler_test ${POMAGMA_CHART_TEST_LIBS})
add_test(NAME chart_scheduler COMMAND chart_scheduler_test)

