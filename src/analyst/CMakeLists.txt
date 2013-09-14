
include_directories(${CMAKE_SOURCE_DIR}/)

add_library(pomagma_analyst SHARED
	simplify.cpp
	approximate.cpp
	)
set(POMAGMA_ANALYST_LIBS
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
target_link_libraries(simplify ${POMAGMA_ANALYST_LIBS})

add_executable(analyst server_main.cpp server.cpp messages.pb.cc)
target_link_libraries(analyst ${POMAGMA_ANALYST_LIBS} zmq)
