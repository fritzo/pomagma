include_directories(${CMAKE_SOURCE_DIR}/include)

add_library(pomagma_atlas SHARED
	structure.pb.cc
	program.cpp
)
target_link_libraries(pomagma_atlas
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

add_executable(atlas_protobuf_test protobuf_test.cpp)
target_link_libraries(atlas_protobuf_test
	pomagma_atlas
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
add_test(NAME atlas_protobuf COMMAND atlas_protobuf_test)

add_subdirectory(micro)
add_subdirectory(macro)
add_subdirectory(shard)
