include_directories(${CMAKE_SOURCE_DIR}/include)

add_executable(protobuf_stream_test stream_test.cpp)
target_link_libraries(protobuf_stream_test
	pomagma_platform_sequential
	${POMAGMA_SEQUENTIAL_LIBS})
add_test(protobuf_stream protobuf_stream_test)
