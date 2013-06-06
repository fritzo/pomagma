
include_directories(${CMAKE_SOURCE_DIR}/)

add_executable(concurrent_dense_set_test dense_set_test.cpp)
target_link_libraries(concurrent_dense_set_test
	pomagma_platform_concurrent
       	${POMAGMA_CONCURRENT_LIBS})
add_test(NAME concurrent_dense_set COMMAND concurrent_dense_set_test)
add_executable(concurrent_dense_set_profile dense_set_profile.cpp)
target_link_libraries(concurrent_dense_set_profile
	pomagma_platform_concurrent
       	${POMAGMA_CONCURRENT_LIBS})

