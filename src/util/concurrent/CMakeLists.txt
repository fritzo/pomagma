include_directories(${CMAKE_SOURCE_DIR}/include)

add_executable(concurrent_dense_set_test dense_set_test.cpp)
target_link_libraries(concurrent_dense_set_test ${POMAGMA_UTIL_LIBS})
add_test(NAME util_concurrent_dense_set COMMAND concurrent_dense_set_test)

add_executable(concurrent_dense_set_profile dense_set_profile.cpp)
target_link_libraries(concurrent_dense_set_profile ${POMAGMA_UTIL_LIBS})

