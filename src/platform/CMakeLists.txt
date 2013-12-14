
include_directories(${CMAKE_SOURCE_DIR}/)

add_library(pomagma_platform_sequential SHARED
	util.cpp
	aligned_alloc.cpp
	sequential/dense_set.cpp
	hdf5.cpp
	)

add_library(pomagma_platform_concurrent SHARED
	util.cpp
	aligned_alloc.cpp
	concurrent/dense_set.cpp
	hdf5.cpp
	)

add_executable(threading_profile threading_profile.cpp)
target_link_libraries(threading_profile
	pomagma_platform_concurrent
       	${POMAGMA_CONCURRENT_LIBS})

add_executable(worker_pool_test worker_pool_test.cpp)
target_link_libraries(worker_pool_test
	pomagma_platform_sequential
	${POMAGMA_SEQUENTIAL_LIBS}
	tbb)
add_test(NAME worker_pool COMMAND worker_pool_test)

add_subdirectory(concurrent)
add_subdirectory(sequential)
