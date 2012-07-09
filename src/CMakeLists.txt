
#include_directories(${CMAKE_SOURCE_DIR}/)

add_library(pomagma SHARED
	util.cpp
	aligned_alloc.cpp
	dense_set.cpp
	dense_bin_rel.cpp
	dense_bin_fun.cpp
	dense_sym_fun.cpp
	sparse_bin_fun.cpp
	)
install(TARGETS pomagma LIBRARY DESTINATION /usr/lib)

add_executable(dense_set_test dense_set_test.cpp)
target_link_libraries(dense_set_test pomagma)
add_test(NAME dense_set COMMAND dense_set_test)

add_executable(binary_relation_test binary_relation_test.cpp)
target_link_libraries(binary_relation_test pomagma)
add_test(NAME binary_relation COMMAND binary_relation_test)

add_executable(dense_sym_fun_test dense_sym_fun_test.cpp)
target_link_libraries(dense_sym_fun_test pomagma)
add_test(NAME dense_sym_fun COMMAND dense_sym_fun_test)

#install(TARGETS pomagma LIBRARY DESTINATION ${LIBRARY_OUTPUT_PATH})

