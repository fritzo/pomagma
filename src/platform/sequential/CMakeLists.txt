
include_directories(${CMAKE_SOURCE_DIR}/)

add_executable(sequential_dense_set_test dense_set_test.cpp)
target_link_libraries(sequential_dense_set_test
	pomagma_platform_sequential
       	${POMAGMA_CONCURRENT_LIBS})
add_test(NAME sequential_dense_set COMMAND sequential_dense_set_test)
add_executable(sequential_dense_set_profile dense_set_profile.cpp)
target_link_libraries(sequential_dense_set_profile
	pomagma_platform_sequential
       	${POMAGMA_CONCURRENT_LIBS})

