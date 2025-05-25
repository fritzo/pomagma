include_directories(${CMAKE_SOURCE_DIR}/include)

add_library(pomagma_language SHARED
	language.cpp
	language.pb.cc
)
target_link_libraries(pomagma_language
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

add_custom_command(
	OUTPUT ${CMAKE_CURRENT_LIST_DIR}/language.pb.cc
	COMMAND protoc ${CMAKE_CURRENT_LIST_DIR}/language.proto
		--proto_path=${CMAKE_CURRENT_LIST_DIR}
		--cpp_out=${CMAKE_CURRENT_LIST_DIR}
	DEPENDS ${CMAKE_CURRENT_LIST_DIR}/language.proto
)
