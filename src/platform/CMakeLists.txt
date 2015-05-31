include_directories(${CMAKE_SOURCE_DIR}/include)

add_library(pomagma_platform_sequential SHARED
	util.cpp
	aligned_alloc.cpp
	sequential/dense_set.cpp
	hasher.cpp
	blobstore.cpp
	profiler.cpp
	hdf5.cpp
)

add_library(pomagma_platform_concurrent SHARED
	util.cpp
	aligned_alloc.cpp
	concurrent/dense_set.cpp
	hasher.cpp
	blobstore.cpp
	profiler.cpp
	hdf5.cpp
)

add_executable(util_test util_test.cpp)
target_link_libraries(util_test
	pomagma_platform_sequential
	${POMAGMA_SEQUENTIAL_LIBS})
add_test(NAME util COMMAND util_test)

add_executable(hasher_test hasher_test.cpp)
target_link_libraries(hasher_test
	pomagma_platform_sequential
	${POMAGMA_SEQUENTIAL_LIBS})
add_test(NAME hasher COMMAND hasher_test)

add_executable(threading_profile threading_profile.cpp)
target_link_libraries(threading_profile
	pomagma_platform_concurrent
	${POMAGMA_CONCURRENT_LIBS})

add_executable(worker_pool_test worker_pool_test.cpp)
target_link_libraries(worker_pool_test
	pomagma_platform_sequential
	${POMAGMA_SEQUENTIAL_LIBS})
add_test(NAME worker_pool COMMAND worker_pool_test)

add_executable(async_map_test async_map_test.cpp)
target_link_libraries(async_map_test
	pomagma_platform_sequential
	${POMAGMA_SEQUENTIAL_LIBS})
add_test(NAME async_map COMMAND async_map_test)

add_subdirectory(concurrent)
add_subdirectory(sequential)
