
#include_directories(${CMAKE_SOURCE_DIR}/)

add_library(pomagma SHARED
	util.cpp
	aligned_alloc.cpp
	dense_set.cpp
	carrier.cpp
	base_bin_rel.cpp
	binary_relation.cpp
	binary_function.cpp
	symmetric_function.cpp
	inverse_bin_fun.cpp
	)
install(TARGETS pomagma LIBRARY DESTINATION ${PROJECT_SOURCE_DIR}/lib)

add_executable(dense_set_test dense_set_test.cpp)
target_link_libraries(dense_set_test pomagma tbb)
add_test(NAME dense_set COMMAND dense_set_test)

add_executable(carrier_test carrier_test.cpp)
target_link_libraries(carrier_test pomagma tbb)
add_test(NAME carrier COMMAND carrier_test)

add_executable(binary_relation_test binary_relation_test.cpp)
target_link_libraries(binary_relation_test pomagma tbb)
add_test(NAME binary_relation COMMAND binary_relation_test)

add_executable(binary_function_test binary_function_test.cpp)
target_link_libraries(binary_function_test pomagma tbb)
add_test(NAME binary_function COMMAND binary_function_test)

add_executable(symmetric_function_test symmetric_function_test.cpp)
target_link_libraries(symmetric_function_test pomagma tbb)
add_test(NAME symmetric_function COMMAND symmetric_function_test)

add_executable(inverse_bin_fun_test inverse_bin_fun_test.cpp)
target_link_libraries(inverse_bin_fun_test pomagma tbb)
add_test(NAME inverse_bin_fun COMMAND inverse_bin_fun_test)

#install(TARGETS pomagma LIBRARY DESTINATION ${LIBRARY_OUTPUT_PATH})

