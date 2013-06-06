
include_directories(${CMAKE_SOURCE_DIR}/)


set(POMAGMA_PLATFORM_TEST_LIBS
	boost_thread
	tbb
       	hdf5_hl hdf5
	crypto ssl
	protobuf
	)


add_executable(threading_profile threading_profile.cpp)
target_link_libraries(threading_profile
	pomagma_platform_concurrent
       	${POMAGMA_PLATFORM_TEST_LIBS}
	)

add_executable(sequential_dense_set_test sequential_dense_set_test.cpp)
target_link_libraries(sequential_dense_set_test
	pomagma_platform_sequential
       	${POMAGMA_PLATFORM_TEST_LIBS}
	)
add_test(NAME sequential_dense_set COMMAND sequential_dense_set_test)
add_executable(sequential_dense_set_profile sequential_dense_set_profile.cpp)
target_link_libraries(sequential_dense_set_profile
	pomagma_platform_sequential
       	${POMAGMA_PLATFORM_TEST_LIBS}
	)

add_executable(concurrent_dense_set_test concurrent_dense_set_test.cpp)
target_link_libraries(concurrent_dense_set_test
	pomagma_platform_concurrent
       	${POMAGMA_PLATFORM_TEST_LIBS}
	)
add_test(NAME concurrent_dense_set COMMAND concurrent_dense_set_test)
add_executable(concurrent_dense_set_profile concurrent_dense_set_profile.cpp)
target_link_libraries(concurrent_dense_set_profile
	pomagma_platform_concurrent
       	${POMAGMA_PLATFORM_TEST_LIBS}
	)

