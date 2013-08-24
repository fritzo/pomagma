
include_directories(${CMAKE_SOURCE_DIR}/)

add_library(pomagma_analyst SHARED
	simplify.cpp
	approximate.cpp
	)
set(POMAGMA_THEORIST_LIBS
	pomagma_analyst
	pomagma_macrostructure
	pomagma_platform_sequential
	pomagma_language
	${POMAGMA_SEQUENTIAL_LIBS}
	)

add_custom_command(
	OUTPUT ${CMAKE_CURRENT_LIST_DIR}/messages.pb.cc
	COMMAND protoc ${CMAKE_CURRENT_LIST_DIR}/messages.proto
		--proto_path=${CMAKE_CURRENT_LIST_DIR}
		--cpp_out=${CMAKE_CURRENT_LIST_DIR}
	DEPENDS ${CMAKE_CURRENT_LIST_DIR}/messages.proto
	)

add_executable(simplify simplify_main.cpp)
target_link_libraries(simplify ${POMAGMA_THEORIST_LIBS})

add_executable(serve server_main.cpp server.cpp messages.pb.cc)
target_link_libraries(serve ${POMAGMA_THEORIST_LIBS} zmq)
