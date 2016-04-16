include_directories(${CMAKE_SOURCE_DIR}/include)

add_library(pomagma_language SHARED
	language.cpp
	language.pb.cc
)
target_link_libraries(pomagma_language
	${POMAGMA_UTIL_LIBS}
	${PROTOBUF_LIBRARIES}
)

add_custom_command(
	OUTPUT ${CMAKE_CURRENT_LIST_DIR}/language.pb.cc
	COMMAND protoc ${CMAKE_CURRENT_LIST_DIR}/language.proto
		--proto_path=${CMAKE_CURRENT_LIST_DIR}
		--cpp_out=${CMAKE_CURRENT_LIST_DIR}
	DEPENDS ${CMAKE_CURRENT_LIST_DIR}/language.proto
)
