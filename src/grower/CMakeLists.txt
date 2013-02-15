
#include_directories(${CMAKE_SOURCE_DIR}/)

add_library(pomagma_grower SHARED
	util.cpp
	aligned_alloc.cpp
	dense_set.cpp
	carrier.cpp
	base_bin_rel.cpp
	binary_relation.cpp
	nullary_function.cpp
	injective_function.cpp
	binary_function.cpp
	symmetric_function.cpp
	sampler.cpp
	structure.cpp
	scheduler.cpp
	)
install(TARGETS pomagma_grower LIBRARY DESTINATION ${PROJECT_SOURCE_DIR}/lib)
set(POMAGMA_LIBS
	pomagma_grower
       	boost_thread
       	tbb
       	hdf5_hl hdf5)


add_library(pomagma_grower_dummy SHARED dummy.theory.cpp)
set(POMAGMA_TEST_LIBS
	pomagma_grower
	pomagma_grower_dummy
	boost_thread
	tbb
       	hdf5_hl hdf5)


add_executable(threading_profile threading_profile.cpp)
target_link_libraries(threading_profile ${POMAGMA_TEST_LIBS})

add_executable(dense_set_test dense_set_test.cpp)
target_link_libraries(dense_set_test ${POMAGMA_TEST_LIBS})
add_test(NAME dense_set COMMAND dense_set_test)
add_executable(dense_set_profile dense_set_profile.cpp)
target_link_libraries(dense_set_profile ${POMAGMA_TEST_LIBS})

add_executable(carrier_test carrier_test.cpp)
target_link_libraries(carrier_test ${POMAGMA_TEST_LIBS})
add_test(NAME carrier COMMAND carrier_test)

add_executable(binary_relation_test binary_relation_test.cpp)
target_link_libraries(binary_relation_test ${POMAGMA_TEST_LIBS})
add_test(NAME binary_relation COMMAND binary_relation_test)

add_executable(nullary_function_test nullary_function_test.cpp)
target_link_libraries(nullary_function_test ${POMAGMA_TEST_LIBS})
add_test(NAME nullary_function COMMAND nullary_function_test)

add_executable(injective_function_test injective_function_test.cpp)
target_link_libraries(injective_function_test ${POMAGMA_TEST_LIBS})
add_test(NAME injective_function COMMAND injective_function_test)

add_executable(binary_function_test binary_function_test.cpp)
target_link_libraries(binary_function_test ${POMAGMA_TEST_LIBS})
add_test(NAME binary_function COMMAND binary_function_test)

add_executable(symmetric_function_test symmetric_function_test.cpp)
target_link_libraries(symmetric_function_test ${POMAGMA_TEST_LIBS})
add_test(NAME symmetric_function COMMAND symmetric_function_test)

#add_executable(inverse_bin_fun_test inverse_bin_fun_test.cpp)
#target_link_libraries(inverse_bin_fun_test ${POMAGMA_TEST_LIBS})
#add_test(NAME inverse_bin_fun COMMAND inverse_bin_fun_test)

add_executable(scheduler_test scheduler_test.cpp)
target_link_libraries(scheduler_test ${POMAGMA_TEST_LIBS})
add_test(NAME scheduler COMMAND scheduler_test)


add_library(pomagma_grower_server SHARED
	server.cpp
	language.pb.cc
	structure.pb.cc
	)
install(TARGETS pomagma_grower_server LIBRARY
       	DESTINATION ${PROJECT_SOURCE_DIR}/lib
	)
set(POMAGMA_SERVER_LIBS
	pomagma_grower_server
	${POMAGMA_LIBS}
	#zmq
	protobuf
	)


add_executable(dummy.grower dummy.theory.cpp)
target_link_libraries(dummy.grower ${POMAGMA_SERVER_LIBS})

set(SRC_DIR ${PROJECT_SOURCE_DIR}/src)

# TODO abstract these out as functions

add_custom_command(
	OUTPUT ${CMAKE_CURRENT_LIST_DIR}/language.pb.cc
	COMMAND protoc ${SRC_DIR}/language/language.proto
		--proto_path=${SRC_DIR}/language
		--cpp_out=${CMAKE_CURRENT_LIST_DIR}
	DEPENDS ${SRC_DIR}/language/language.proto
	)

add_custom_command(
	OUTPUT ${CMAKE_CURRENT_LIST_DIR}/structure.pb.cc
	COMMAND protoc ${SRC_DIR}/structure/structure.proto
		--proto_path=${SRC_DIR}/structure
		--cpp_out=${CMAKE_CURRENT_LIST_DIR}
	DEPENDS ${SRC_DIR}/structure/structure.proto
	)

add_custom_command(
	OUTPUT ${CMAKE_CURRENT_LIST_DIR}/h4.theory.cpp
	COMMAND python ${SRC_DIR}/compiler/run.py compile
		${SRC_DIR}/theory/group.rules
		${SRC_DIR}/theory/h4.rules
		${SRC_DIR}/theory/h4.facts
		outfile=${CMAKE_CURRENT_LIST_DIR}/h4.theory.cpp
		extensional=false
	DEPENDS ${SRC_DIR}/compiler/util.py
		${SRC_DIR}/compiler/expressions.py
		${SRC_DIR}/compiler/sequents.py
		${SRC_DIR}/compiler/parser.py
		${SRC_DIR}/compiler/compiler.py
		${SRC_DIR}/compiler/cpp.py
		${SRC_DIR}/compiler/run.py
		${SRC_DIR}/theory/group.rules
		${SRC_DIR}/theory/h4.rules
		${SRC_DIR}/theory/h4.facts
	)
add_executable(h4.grower h4.theory.cpp)
target_link_libraries(h4.grower ${POMAGMA_SERVER_LIBS})
install(TARGETS h4.grower DESTINATION ${PROJECT_SOURCE_DIR}/bin)

add_custom_command(
	OUTPUT ${CMAKE_CURRENT_LIST_DIR}/sk.theory.cpp
	COMMAND python ${SRC_DIR}/compiler/run.py compile
		${SRC_DIR}/theory/sk.rules
		${SRC_DIR}/theory/sk.facts
		${SRC_DIR}/theory/order.facts
		outfile=${CMAKE_CURRENT_LIST_DIR}/sk.theory.cpp
	DEPENDS ${SRC_DIR}/compiler/util.py
		${SRC_DIR}/compiler/expressions.py
		${SRC_DIR}/compiler/sequents.py
		${SRC_DIR}/compiler/parser.py
		${SRC_DIR}/compiler/extensional.py
		${SRC_DIR}/compiler/compiler.py
		${SRC_DIR}/compiler/cpp.py
		${SRC_DIR}/compiler/run.py
		${SRC_DIR}/theory/sk.rules
		${SRC_DIR}/theory/sk.facts
		${SRC_DIR}/theory/order.facts
	)
add_executable(sk.grower sk.theory.cpp)
target_link_libraries(sk.grower ${POMAGMA_SERVER_LIBS})
install(TARGETS sk.grower DESTINATION ${PROJECT_SOURCE_DIR}/bin)

add_custom_command(
	OUTPUT ${CMAKE_CURRENT_LIST_DIR}/skj.theory.cpp
	COMMAND python ${SRC_DIR}/compiler/run.py compile
		${SRC_DIR}/theory/sk.rules
		${SRC_DIR}/theory/join.rules
		${SRC_DIR}/theory/sk.facts
		${SRC_DIR}/theory/order.facts
		outfile=${CMAKE_CURRENT_LIST_DIR}/skj.theory.cpp
	DEPENDS ${SRC_DIR}/compiler/util.py
		${SRC_DIR}/compiler/expressions.py
		${SRC_DIR}/compiler/sequents.py
		${SRC_DIR}/compiler/parser.py
		${SRC_DIR}/compiler/extensional.py
		${SRC_DIR}/compiler/compiler.py
		${SRC_DIR}/compiler/cpp.py
		${SRC_DIR}/compiler/run.py
		${SRC_DIR}/theory/sk.rules
		${SRC_DIR}/theory/join.rules
		${SRC_DIR}/theory/sk.facts
		${SRC_DIR}/theory/order.facts
	)
add_executable(skj.grower skj.theory.cpp)
target_link_libraries(skj.grower ${POMAGMA_SERVER_LIBS})
install(TARGETS skj.grower DESTINATION ${PROJECT_SOURCE_DIR}/bin)
