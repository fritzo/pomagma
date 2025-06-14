include_directories(${CMAKE_SOURCE_DIR})

add_custom_command(
	OUTPUT ${CMAKE_CURRENT_LIST_DIR}/cartographer_messages.pb.cc
	COMMAND protoc ${CMAKE_CURRENT_LIST_DIR}/cartographer_messages.proto
		--proto_path=${CMAKE_CURRENT_LIST_DIR}
		--cpp_out=${CMAKE_CURRENT_LIST_DIR}
	DEPENDS ${CMAKE_CURRENT_LIST_DIR}/cartographer_messages.proto
)

pomagma_add_executable(cartographer
	main.cpp
       	server.cpp
	signature.cpp
	aggregate.cpp
	trim.cpp
	infer.cpp
	../theorist/assume.cpp
	../theorist/consistency.cpp
	../theorist/conjecture_diverge.cpp
	../theorist/conjecture_equal.cpp
	../theorist/hypothesize.cpp
       	cartographer_messages.pb.cc
)

# Use vcpkg ZeroMQ if available, otherwise fallback to system ZMQ
if(cppzmq_FOUND)
	target_link_libraries(cartographer
		cppzmq
		${POMAGMA_WORLD_LIBS}
	)
else()
	target_link_libraries(cartographer
		${ZMQ_LIBRARIES}
		${POMAGMA_WORLD_LIBS}
	)
endif()
