
#include_directories(${CMAKE_SOURCE_DIR}/)

add_library(pomagma SHARED
	util.cpp
	aligned_alloc.cpp
	dense_set.cpp
	carrier.cpp
	base_bin_rel.cpp
	binary_relation.cpp
	nullary_function.cpp
	unary_function.cpp
	binary_function.cpp
	symmetric_function.cpp
	inverse_bin_fun.cpp
	task_manager.cpp
	)
install(TARGETS pomagma LIBRARY DESTINATION ${PROJECT_SOURCE_DIR}/lib)
set(POMAGMA_LIBS pomagma boost_thread tbb)


add_library(pomagma_dummy SHARED dummy.theory.cpp)
#install(TARGETS pomagma LIBRARY DESTINATION ${PROJECT_SOURCE_DIR}/lib)
set(POMAGMA_TEST_LIBS pomagma pomagma_dummy boost_thread tbb)


add_executable(dense_set_test dense_set_test.cpp)
target_link_libraries(dense_set_test ${POMAGMA_TEST_LIBS})
add_test(NAME dense_set COMMAND dense_set_test)

add_executable(carrier_test carrier_test.cpp)
target_link_libraries(carrier_test ${POMAGMA_TEST_LIBS})
add_test(NAME carrier COMMAND carrier_test)

add_executable(binary_relation_test binary_relation_test.cpp)
target_link_libraries(binary_relation_test ${POMAGMA_TEST_LIBS})
add_test(NAME binary_relation COMMAND binary_relation_test)

add_executable(nullary_function_test nullary_function_test.cpp)
target_link_libraries(nullary_function_test ${POMAGMA_TEST_LIBS})
add_test(NAME nullary_function COMMAND nullary_function_test)

add_executable(unary_function_test unary_function_test.cpp)
target_link_libraries(unary_function_test ${POMAGMA_TEST_LIBS})
add_test(NAME unary_function COMMAND unary_function_test)

add_executable(binary_function_test binary_function_test.cpp)
target_link_libraries(binary_function_test ${POMAGMA_TEST_LIBS})
add_test(NAME binary_function COMMAND binary_function_test)

add_executable(symmetric_function_test symmetric_function_test.cpp)
target_link_libraries(symmetric_function_test ${POMAGMA_TEST_LIBS})
add_test(NAME symmetric_function COMMAND symmetric_function_test)

add_executable(inverse_bin_fun_test inverse_bin_fun_test.cpp)
target_link_libraries(inverse_bin_fun_test ${POMAGMA_TEST_LIBS})
add_test(NAME inverse_bin_fun COMMAND inverse_bin_fun_test)

add_executable(task_manager_test task_manager_test.cpp)
target_link_libraries(task_manager_test ${POMAGMA_TEST_LIBS})
add_test(NAME task_manger COMMAND task_manager_test)


add_library(pomagma_server SHARED
	server.cpp
	)
install(TARGETS pomagma_server LIBRARY DESTINATION ${PROJECT_SOURCE_DIR}/lib)
set(POMAGMA_SERVER_LIBS pomagma_server ${POMAGMA_LIBS} zmq)


add_executable(dummy.server dummy.theory.cpp)
target_link_libraries(dummy.server ${POMAGMA_SERVER_LIBS})
