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
	${TBB_LIBRARIES}
	OpenSSL::Crypto OpenSSL::SSL
	${Boost_FILESYSTEM_LIBRARY}
	${Boost_SYSTEM_LIBRARY}
)

set_source_files_properties(gtest_main.cpp COMPILE_FLAGS ${GTEST_FLAGS})
add_library(pomagma_gtest_main SHARED gtest_main.cpp)
target_link_libraries(pomagma_gtest_main pomagma_util gtest)

function(add_unit_test T)
	pomagma_add_executable(${T}_test ${T}_test.cpp)
	set_source_files_properties(${T}_test.cpp COMPILE_FLAGS ${GTEST_FLAGS})
	target_link_libraries(${T}_test ${POMAGMA_UTIL_LIBS} pomagma_gtest_main)
	add_test(NAME util_${T} COMMAND ${T}_test)
endfunction()

add_unit_test(queue)
add_unit_test(hasher)
add_unit_test(worker_pool)
add_unit_test(async_map)
add_unit_test(lazy_map)
add_unit_test(dense_set_store)

pomagma_add_executable(queue_profile queue_profile.cpp)
target_link_libraries(queue_profile ${POMAGMA_UTIL_LIBS})

pomagma_add_executable(threading_profile threading_profile.cpp)
target_link_libraries(threading_profile ${POMAGMA_UTIL_LIBS})

add_subdirectory(concurrent)
add_subdirectory(sequential)
