include_directories(${CMAKE_SOURCE_DIR}/include)

add_library(pomagma_util SHARED
	util.cpp
	aligned_alloc.cpp
	sequential/dense_set.cpp
	concurrent/dense_set.cpp
	dense_set_store.cpp
	queue.cpp
	hasher.cpp
	profiler.cpp
)

add_executable(queue_test queue_test.cpp)
target_link_libraries(queue_test ${POMAGMA_UTIL_LIBS})
add_test(NAME queue COMMAND queue_test)
add_executable(queue_profile queue_profile.cpp)
target_link_libraries(queue_profile ${POMAGMA_UTIL_LIBS})

add_executable(hasher_test hasher_test.cpp)
target_link_libraries(hasher_test ${POMAGMA_UTIL_LIBS})
add_test(NAME hasher COMMAND hasher_test)

add_executable(threading_profile threading_profile.cpp)
target_link_libraries(threading_profile ${POMAGMA_UTIL_LIBS})

add_executable(worker_pool_test worker_pool_test.cpp)
target_link_libraries(worker_pool_test ${POMAGMA_UTIL_LIBS})
add_test(NAME worker_pool COMMAND worker_pool_test)

add_executable(dense_set_store_test dense_set_store_test.cpp)
target_link_libraries(dense_set_store_test ${POMAGMA_UTIL_LIBS})
add_test(NAME dense_set_store COMMAND dense_set_store_test)

add_executable(async_map_test async_map_test.cpp)
target_link_libraries(async_map_test ${POMAGMA_UTIL_LIBS})
add_test(NAME async_map COMMAND async_map_test)

add_executable(lazy_map_test lazy_map_test.cpp)
target_link_libraries(lazy_map_test ${POMAGMA_UTIL_LIBS})
add_test(NAME lazy_map COMMAND lazy_map_test)

add_subdirectory(concurrent)
add_subdirectory(sequential)
