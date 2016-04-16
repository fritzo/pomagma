include_directories(${CMAKE_SOURCE_DIR}/include)

add_library(pomagma_io SHARED
	blobstore.cpp
	protobuf.cpp
)
target_link_libraries(pomagma_io
	${PROTOBUF_LIBRARIES}
	${POMAGMA_UTIL_LIBS}
)

add_executable(io_protobuf_test protobuf_test.cpp protobuf_test.pb.cc)
target_link_libraries(io_protobuf_test
	${POMAGMA_IO_LIBS}
	${POMAGMA_UTIL_LIBS}
)
add_test(NAME io_protobuf COMMAND io_protobuf_test)

add_executable(io_message_test message_test.cpp)
target_link_libraries(io_message_test
	${POMAGMA_IO_LIBS}
	${POMAGMA_UTIL_LIBS}
)
add_test(NAME io_message COMMAND io_message_test)
add_executable(io_message_profile message_profile.cpp)
target_link_libraries(io_message_profile
	${POMAGMA_IO_LIBS}
	${POMAGMA_UTIL_LIBS}
)
