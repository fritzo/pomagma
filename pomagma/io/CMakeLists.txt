include_directories(${CMAKE_SOURCE_DIR})

add_library(pomagma_io SHARED
	blobstore.cpp
	protobuf.cpp
)
target_link_libraries(pomagma_io
	protobuf::libprotobuf
	absl::log
	absl::log_internal_message
	absl::log_internal_check_op
	absl::log_internal_format
	absl::base
	absl::strings
	absl::str_format
	${POMAGMA_UTIL_LIBS}
)

pomagma_add_executable(io_protobuf_test protobuf_test.cpp protobuf_test.pb.cc)
target_link_libraries(io_protobuf_test
	protobuf::libprotobuf
	absl::log
	absl::log_internal_message
	absl::log_internal_check_op
	absl::log_internal_format
	absl::base
	absl::strings
	absl::str_format
	${POMAGMA_IO_LIBS}
	${POMAGMA_UTIL_LIBS}
)
add_test(NAME io_protobuf COMMAND io_protobuf_test)

pomagma_add_executable(io_message_test message_test.cpp)
target_link_libraries(io_message_test
	${POMAGMA_IO_LIBS}
	${POMAGMA_UTIL_LIBS}
)
add_test(NAME io_message COMMAND io_message_test)

pomagma_add_executable(io_message_profile message_profile.cpp)
target_link_libraries(io_message_profile
	${POMAGMA_IO_LIBS}
	${POMAGMA_UTIL_LIBS}
)
