
include_directories(${CMAKE_SOURCE_DIR}/)

add_custom_command(
	OUTPUT ${CMAKE_CURRENT_LIST_DIR}/messages.pb.cc
	COMMAND protoc ${CMAKE_CURRENT_LIST_DIR}/messages.proto
		--proto_path=${CMAKE_CURRENT_LIST_DIR}
		--cpp_out=${CMAKE_CURRENT_LIST_DIR}
	DEPENDS ${CMAKE_CURRENT_LIST_DIR}/messages.proto
	)

add_executable(cartographer
	main.cpp
       	server.cpp
	signature.cpp
	aggregate.cpp
	trim.cpp
	infer.cpp
	../theorist/assume.cpp
	../theorist/consistency.cpp
       	messages.pb.cc
	)
target_link_libraries(cartographer
	pomagma_macrostructure
	pomagma_platform_sequential
	pomagma_language
	${POMAGMA_SEQUENTIAL_LIBS}
	zmq
	)
