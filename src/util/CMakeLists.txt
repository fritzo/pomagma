include_directories(${CMAKE_SOURCE_DIR}/include)

add_library(pomagma_util SHARED
	util.cpp
	threading.cpp
	aligned_alloc.cpp
	sequential/dense_set.cpp
	concurrent/dense_set.cpp
	dense_set_store.cpp
	queue.cpp
	hasher.cpp
	profiler.cpp
)
target_link_libraries(pomagma_util
	pomagma_farmhash
	tbb
	crypto ssl
	${Boost_FILESYSTEM_LIBRARY}
	${Boost_SYSTEM_LIBRARY}
)

function(add_unit_test N)
	add_executable(${N}_test ${N}_test.cpp)
	set_source_files_properties(${N}_test.cpp COMPILE_FLAGS ${GTEST_FLAGS})
	target_link_libraries(${N}_test ${POMAGMA_UTIL_LIBS} gtest_main)
	add_test(NAME util_${N} COMMAND ${N}_test)
endfunction()

add_unit_test(queue)
add_unit_test(hasher)

add_executable(queue_profile queue_profile.cpp)
target_link_libraries(queue_profile ${POMAGMA_UTIL_LIBS})

add_executable(threading_profile threading_profile.cpp)
target_link_libraries(threading_profile ${POMAGMA_UTIL_LIBS})

add_executable(worker_pool_test worker_pool_test.cpp)
target_link_libraries(worker_pool_test ${POMAGMA_UTIL_LIBS})
add_test(NAME util_worker_pool COMMAND worker_pool_test)

add_executable(dense_set_store_test dense_set_store_test.cpp)
target_link_libraries(dense_set_store_test ${POMAGMA_UTIL_LIBS})
add_test(NAME util_dense_set_store COMMAND dense_set_store_test)

add_executable(async_map_test async_map_test.cpp)
target_link_libraries(async_map_test ${POMAGMA_UTIL_LIBS})
add_test(NAME util_async_map COMMAND async_map_test)

add_executable(lazy_map_test lazy_map_test.cpp)
target_link_libraries(lazy_map_test ${POMAGMA_UTIL_LIBS})
add_test(NAME util_lazy_map COMMAND lazy_map_test)

add_subdirectory(concurrent)
add_subdirectory(sequential)
