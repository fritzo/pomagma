
include_directories(${CMAKE_SOURCE_DIR}/)


add_library(pomagma_util_sequential SHARED
	util.cpp
	aligned_alloc.cpp
	sequential_dense_set.cpp)
add_library(pomagma_util_concurrent SHARED
	util.cpp
	aligned_alloc.cpp
	concurrent_dense_set.cpp)
set(POMAGMA_UTIL_TEST_LIBS
	boost_thread
	tbb
       	hdf5_hl hdf5
	crypto ssl)


add_executable(threading_profile threading_profile.cpp)
target_link_libraries(threading_profile
       	${POMAGMA_UTIL_TEST_LIBS}
	pomagma_util_concurrent)

add_executable(sequential_dense_set_test sequential_dense_set_test.cpp)
target_link_libraries(sequential_dense_set_test
       	${POMAGMA_UTIL_TEST_LIBS}
	pomagma_util_sequential)
add_test(NAME sequential_dense_set COMMAND sequential_dense_set_test)
add_executable(sequential_dense_set_profile sequential_dense_set_profile.cpp)
target_link_libraries(sequential_dense_set_profile
       	${POMAGMA_UTIL_TEST_LIBS}
	pomagma_util_sequential)

add_executable(concurrent_dense_set_test concurrent_dense_set_test.cpp)
target_link_libraries(concurrent_dense_set_test
       	${POMAGMA_UTIL_TEST_LIBS}
	pomagma_util_concurrent)
add_test(NAME concurrent_dense_set COMMAND concurrent_dense_set_test)
add_executable(concurrent_dense_set_profile concurrent_dense_set_profile.cpp)
target_link_libraries(concurrent_dense_set_profile
       	${POMAGMA_UTIL_TEST_LIBS}
	pomagma_util_concurrent)

