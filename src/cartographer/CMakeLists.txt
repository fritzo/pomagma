
include_directories(${CMAKE_SOURCE_DIR}/)

add_library(pomagma_cartographer SHARED
	signature.cpp
	aggregate.cpp
	trim.cpp
	infer.cpp
	)
set(POMAGMA_CARTOGRAPHER_LIBS
	pomagma_cartographer
	pomagma_macrostructure
	pomagma_platform_sequential
	pomagma_language
	${POMAGMA_SEQUENTIAL_LIBS})

add_custom_command(
	OUTPUT ${CMAKE_CURRENT_LIST_DIR}/messages.pb.cc
	COMMAND protoc ${CMAKE_CURRENT_LIST_DIR}/messages.proto
		--proto_path=${CMAKE_CURRENT_LIST_DIR}
		--cpp_out=${CMAKE_CURRENT_LIST_DIR}
	DEPENDS ${CMAKE_CURRENT_LIST_DIR}/messages.proto
	)

add_executable(validate validate_main.cpp)
target_link_libraries(validate ${POMAGMA_CARTOGRAPHER_LIBS})

add_executable(copy copy_main.cpp)
target_link_libraries(copy ${POMAGMA_CARTOGRAPHER_LIBS})

add_executable(aggregate aggregate_main.cpp)
target_link_libraries(aggregate ${POMAGMA_CARTOGRAPHER_LIBS})

add_executable(trim trim_main.cpp)
target_link_libraries(trim ${POMAGMA_CARTOGRAPHER_LIBS})

add_executable(infer infer_main.cpp)
target_link_libraries(infer ${POMAGMA_CARTOGRAPHER_LIBS})

add_executable(cartographer server_main.cpp server.cpp messages.pb.cc)
target_link_libraries(cartographer ${POMAGMA_CARTOGRAPHER_LIBS} zmq)
