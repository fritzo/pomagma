include_directories(${CMAKE_SOURCE_DIR}/include)

add_library(pomagma_io SHARED
	blobstore.cpp
	protobuf.cpp
	hdf5.cpp
)

add_executable(io_protobuf_test protobuf_test.cpp protobuf_test.pb.cc)
target_link_libraries(io_protobuf_test
	${POMAGMA_IO_LIBS}
	${POMAGMA_UTIL_LIBS}
)
add_test(NAME io_protobuf COMMAND io_protobuf_test)
