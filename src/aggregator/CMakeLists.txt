
include_directories(${CMAKE_SOURCE_DIR}/)

add_library(pomagma_aggregator SHARED
	../util/util.cpp
	../util/aligned_alloc.cpp
	../util/sequential_dense_set.cpp
	carrier.cpp
	base_bin_rel.cpp
	binary_relation.cpp
	nullary_function.cpp
	injective_function.cpp
	binary_function.cpp
	symmetric_function.cpp
	structure.cpp
	aggregator.cpp
	)
install(TARGETS pomagma_aggregator
	LIBRARY
	DESTINATION ${PROJECT_SOURCE_DIR}/lib)
set(POMAGMA_LIBS
	pomagma_aggregator
       	hdf5_hl hdf5
	crypto ssl)


set(POMAGMA_AGGREGATOR_TEST_LIBS
	pomagma_aggregator
       	hdf5_hl hdf5
	crypto ssl)

add_executable(aggregator_carrier_test carrier_test.cpp)
target_link_libraries(aggregator_carrier_test ${POMAGMA_AGGREGATOR_TEST_LIBS})
add_test(NAME aggregator_carrier COMMAND aggregator_carrier_test)

add_executable(binary_relation_test binary_relation_test.cpp)
target_link_libraries(binary_relation_test ${POMAGMA_AGGREGATOR_TEST_LIBS})
add_test(NAME aggregator_binary_relation COMMAND binary_relation_test)

add_executable(nullary_function_test nullary_function_test.cpp)
target_link_libraries(nullary_function_test ${POMAGMA_AGGREGATOR_TEST_LIBS})
add_test(NAME aggregator_nullary_function COMMAND nullary_function_test)

add_executable(injective_function_test injective_function_test.cpp)
target_link_libraries(injective_function_test ${POMAGMA_AGGREGATOR_TEST_LIBS})
add_test(NAME aggregator_injective_function COMMAND injective_function_test)

add_executable(binary_function_test binary_function_test.cpp)
target_link_libraries(binary_function_test ${POMAGMA_AGGREGATOR_TEST_LIBS})
add_test(NAME aggregator_binary_function COMMAND binary_function_test)

add_executable(symmetric_function_test symmetric_function_test.cpp)
target_link_libraries(symmetric_function_test ${POMAGMA_AGGREGATOR_TEST_LIBS})
add_test(NAME aggregator_symmetric_function COMMAND symmetric_function_test)

add_executable(load_item_dim load_item_dim.cpp)
target_link_libraries(load_item_dim ${POMAGMA_LIBS})

#add_library(pomagma_aggregator_server SHARED
#	server.cpp
#	language.pb.cc
#	structure.pb.cc
#	)
#install(TARGETS pomagma_aggregator_server LIBRARY
#	DESTINATION ${PROJECT_SOURCE_DIR}/lib
#	)
#set(POMAGMA_SERVER_LIBS
#	pomagma_aggregator_server
#	${POMAGMA_LIBS}
#	#zmq
#	protobuf
#	)

#set(SRC_DIR ${PROJECT_SOURCE_DIR}/src)

## TODO abstract these out as functions

#add_custom_command(
#	OUTPUT ${CMAKE_CURRENT_LIST_DIR}/language.pb.cc
#	COMMAND protoc ${SRC_DIR}/language/language.proto
#		--proto_path=${SRC_DIR}/language
#		--cpp_out=${CMAKE_CURRENT_LIST_DIR}
#	DEPENDS ${SRC_DIR}/language/language.proto
#	)

#add_custom_command(
#	OUTPUT ${CMAKE_CURRENT_LIST_DIR}/structure.pb.cc
#	COMMAND protoc ${SRC_DIR}/structure/structure.proto
#		--proto_path=${SRC_DIR}/structure
#		--cpp_out=${CMAKE_CURRENT_LIST_DIR}
#	DEPENDS ${SRC_DIR}/structure/structure.proto
#	)

#add_custom_command(
#	OUTPUT ${CMAKE_CURRENT_LIST_DIR}/h4.theory.cpp
#	COMMAND python ${SRC_DIR}/compiler/run.py compile
#		${SRC_DIR}/theory/group.rules
#		${SRC_DIR}/theory/h4.rules
#		${SRC_DIR}/theory/h4.facts
#		outfile=${CMAKE_CURRENT_LIST_DIR}/h4.theory.cpp
#		extensional=false
#	DEPENDS ${SRC_DIR}/compiler/util.py
#		${SRC_DIR}/compiler/expressions.py
#		${SRC_DIR}/compiler/sequents.py
#		${SRC_DIR}/compiler/parser.py
#		${SRC_DIR}/compiler/compiler.py
#		${SRC_DIR}/compiler/cpp.py
#		${SRC_DIR}/compiler/run.py
#		${SRC_DIR}/theory/group.rules
#		${SRC_DIR}/theory/h4.rules
#		${SRC_DIR}/theory/h4.facts
#	)
#add_executable(h4.aggregator h4.theory.cpp)
#target_link_libraries(h4.aggregator ${POMAGMA_SERVER_LIBS})
#install(TARGETS h4.aggregator DESTINATION ${PROJECT_SOURCE_DIR}/bin)

#add_custom_command(
#	OUTPUT ${CMAKE_CURRENT_LIST_DIR}/sk.theory.cpp
#	COMMAND python ${SRC_DIR}/compiler/run.py compile
#		${SRC_DIR}/theory/sk.rules
#		${SRC_DIR}/theory/sk.facts
#		${SRC_DIR}/theory/order.facts
#		outfile=${CMAKE_CURRENT_LIST_DIR}/sk.theory.cpp
#	DEPENDS ${SRC_DIR}/compiler/util.py
#		${SRC_DIR}/compiler/expressions.py
#		${SRC_DIR}/compiler/sequents.py
#		${SRC_DIR}/compiler/parser.py
#		${SRC_DIR}/compiler/extensional.py
#		${SRC_DIR}/compiler/compiler.py
#		${SRC_DIR}/compiler/cpp.py
#		${SRC_DIR}/compiler/run.py
#		${SRC_DIR}/theory/sk.rules
#		${SRC_DIR}/theory/sk.facts
#		${SRC_DIR}/theory/order.facts
#	)
#add_executable(sk.aggregator sk.theory.cpp)
#target_link_libraries(sk.aggregator ${POMAGMA_SERVER_LIBS})
#install(TARGETS sk.aggregator DESTINATION ${PROJECT_SOURCE_DIR}/bin)

#add_custom_command(
#	OUTPUT ${CMAKE_CURRENT_LIST_DIR}/skj.theory.cpp
#	COMMAND python ${SRC_DIR}/compiler/run.py compile
#		${SRC_DIR}/theory/sk.rules
#		${SRC_DIR}/theory/join.rules
#		${SRC_DIR}/theory/sk.facts
#		${SRC_DIR}/theory/order.facts
#		outfile=${CMAKE_CURRENT_LIST_DIR}/skj.theory.cpp
#	DEPENDS ${SRC_DIR}/compiler/util.py
#		${SRC_DIR}/compiler/expressions.py
#		${SRC_DIR}/compiler/sequents.py
#		${SRC_DIR}/compiler/parser.py
#		${SRC_DIR}/compiler/extensional.py
#		${SRC_DIR}/compiler/compiler.py
#		${SRC_DIR}/compiler/cpp.py
#		${SRC_DIR}/compiler/run.py
#		${SRC_DIR}/theory/sk.rules
#		${SRC_DIR}/theory/join.rules
#		${SRC_DIR}/theory/sk.facts
#		${SRC_DIR}/theory/order.facts
#	)
#add_executable(skj.aggregator skj.theory.cpp)
#target_link_libraries(skj.aggregator ${POMAGMA_SERVER_LIBS})
#install(TARGETS skj.aggregator DESTINATION ${PROJECT_SOURCE_DIR}/bin)
