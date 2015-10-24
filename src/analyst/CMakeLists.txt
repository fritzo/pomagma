include_directories(${CMAKE_SOURCE_DIR}/include)

add_custom_command(
	OUTPUT ${CMAKE_CURRENT_LIST_DIR}/messages.pb.cc
	COMMAND protoc ${CMAKE_CURRENT_LIST_DIR}/messages.proto
	--proto_path=${CMAKE_CURRENT_LIST_DIR}
	--cpp_out=${CMAKE_CURRENT_LIST_DIR}
	DEPENDS ${CMAKE_CURRENT_LIST_DIR}/messages.proto
)

add_executable(analyst
	main.cpp
	server.cpp
	simplify.cpp
	approximate.cpp
	cached_approximator.cpp
	intervals.cpp
	propagate.cpp
	corpus.cpp
	validator.cpp
	messages.pb.cc
)
target_link_libraries(analyst
	zmq
	${POMAGMA_WORLD_LIBS}
)
