
include_directories(${CMAKE_SOURCE_DIR}/)

add_library(pomagma_language SHARED
	language.cpp
	language.pb.cc
	)

set(SRC_DIR ${PROJECT_SOURCE_DIR}/src)
add_custom_command(
	OUTPUT ${SRC_DIR}/language/language.pb.cc
	COMMAND protoc ${SRC_DIR}/language/language.proto
		--proto_path=${SRC_DIR}/language
		--cpp_out=${CMAKE_CURRENT_LIST_DIR}/language
	DEPENDS ${SRC_DIR}/language/language.proto
	)
