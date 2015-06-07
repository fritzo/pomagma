include_directories(${CMAKE_SOURCE_DIR}/include)

add_library(pomagma_util SHARED
	util.cpp
	aligned_alloc.cpp
	sequential/dense_set.cpp
	concurrent/dense_set.cpp
	hasher.cpp
	blobstore.cpp
	protobuf.cpp
	profiler.cpp
	hdf5.cpp
)

add_executable(util_protobuf_test protobuf_test.cpp protobuf_test.pb.cc)
target_link_libraries(util_protobuf_test ${POMAGMA_UTIL_LIBS})
add_test(NAME util_protobuf COMMAND util_protobuf_test)

add_executable(hasher_test hasher_test.cpp)
target_link_libraries(hasher_test ${POMAGMA_UTIL_LIBS})
add_test(NAME hasher COMMAND hasher_test)

add_executable(threading_profile threading_profile.cpp)
target_link_libraries(threading_profile ${POMAGMA_UTIL_LIBS})

add_executable(worker_pool_test worker_pool_test.cpp)
target_link_libraries(worker_pool_test ${POMAGMA_UTIL_LIBS})
add_test(NAME worker_pool COMMAND worker_pool_test)

add_executable(async_map_test async_map_test.cpp)
target_link_libraries(async_map_test ${POMAGMA_UTIL_LIBS})
add_test(NAME async_map COMMAND async_map_test)

add_subdirectory(concurrent)
add_subdirectory(sequential)
