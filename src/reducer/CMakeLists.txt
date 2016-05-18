include_directories(${CMAKE_SOURCE_DIR}/include)

add_custom_command(
	OUTPUT ${CMAKE_CURRENT_LIST_DIR}/messages.pb.cc
	COMMAND protoc ${CMAKE_CURRENT_LIST_DIR}/messages.proto
		--proto_path=${CMAKE_CURRENT_LIST_DIR}
		--cpp_out=${CMAKE_CURRENT_LIST_DIR}
	DEPENDS ${CMAKE_CURRENT_LIST_DIR}/messages.proto
)

add_executable(cli
	cli.cpp
	engine.cpp
	io.cpp
)
target_link_libraries(cli
	${POMAGMA_IO_LIBS}
	${POMAGMA_UTIL_LIBS}
)

add_executable(reducer
	main.cpp
	server.cpp
	io.cpp
	engine.cpp
	messages.pb.cc
)
target_link_libraries(reducer
	zmq
	${POMAGMA_IO_LIBS}
	${POMAGMA_UTIL_LIBS}
)
