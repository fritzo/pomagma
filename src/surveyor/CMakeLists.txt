
include_directories(${CMAKE_SOURCE_DIR}/)

set(POMAGMA_SURVEYOR_LIBS
	pomagma_surveyor
       	boost_thread
       	tbb
       	hdf5_hl hdf5
	crypto ssl
	protobuf
	)


add_library(pomagma_surveyor_dummy SHARED dummy.laws.cpp)
set(POMAGMA_SURVEYOR_TEST_LIBS
	pomagma_surveyor
	pomagma_surveyor_dummy
	boost_thread
	tbb
       	hdf5_hl hdf5
	crypto ssl
	protobuf
	)

add_executable(surveyor_carrier_test carrier_test.cpp)
target_link_libraries(surveyor_carrier_test ${POMAGMA_SURVEYOR_TEST_LIBS})
add_test(NAME surveyor_carrier
	COMMAND surveyor_carrier_test)

add_executable(surveyor_binary_relation_test binary_relation_test.cpp)
target_link_libraries(surveyor_binary_relation_test ${POMAGMA_SURVEYOR_TEST_LIBS})
add_test(NAME surveyor_binary_relation
	COMMAND surveyor_binary_relation_test)

add_executable(surveyor_nullary_function_test nullary_function_test.cpp)
target_link_libraries(surveyor_nullary_function_test ${POMAGMA_SURVEYOR_TEST_LIBS})
add_test(NAME surveyor_nullary_function
	COMMAND surveyor_nullary_function_test)

add_executable(surveyor_injective_function_test injective_function_test.cpp)
target_link_libraries(surveyor_injective_function_test ${POMAGMA_SURVEYOR_TEST_LIBS})
add_test(NAME surveyor_injective_function
       COMMAND surveyor_injective_function_test)

add_executable(surveyor_binary_function_test binary_function_test.cpp)
target_link_libraries(surveyor_binary_function_test ${POMAGMA_SURVEYOR_TEST_LIBS})
add_test(NAME surveyor_binary_function
       	COMMAND surveyor_binary_function_test)

add_executable(surveyor_symmetric_function_test symmetric_function_test.cpp)
target_link_libraries(surveyor_symmetric_function_test ${POMAGMA_SURVEYOR_TEST_LIBS})
add_test(NAME surveyor_symmetric_function
	COMMAND surveyor_symmetric_function_test)

add_executable(surveyor_scheduler_test scheduler_test.cpp)
target_link_libraries(surveyor_scheduler_test ${POMAGMA_SURVEYOR_TEST_LIBS})
add_test(NAME surveyor_scheduler
	COMMAND surveyor_scheduler_test)


add_library(pomagma_surveyor_main SHARED main.cpp)
#install(TARGETS pomagma_surveyor_main LIBRARY
#	DESTINATION ${PROJECT_SOURCE_DIR}/lib
#	)
set(POMAGMA_SURVEYOR_MAIN_LIBS
	pomagma_surveyor_main
	${POMAGMA_SURVEYOR_LIBS}
	#zmq
	)


add_executable(dummy.survey dummy.laws.cpp)
target_link_libraries(dummy.survey ${POMAGMA_SURVEYOR_MAIN_LIBS})

set(SRC_DIR ${PROJECT_SOURCE_DIR}/src)

add_custom_command(
	OUTPUT ${CMAKE_CURRENT_LIST_DIR}/h4.laws.cpp
		${SRC_DIR}/laws/h4.compiled
	COMMAND python ${SRC_DIR}/compiler/run.py compile
		${SRC_DIR}/laws/group.rules
		${SRC_DIR}/laws/h4.rules
		${SRC_DIR}/laws/h4.facts
		cpp_out=${CMAKE_CURRENT_LIST_DIR}/h4.laws.cpp
		laws_out=${SRC_DIR}/laws/h4.compiled
		extensional=false
	DEPENDS ${SRC_DIR}/compiler/util.py
		${SRC_DIR}/compiler/expressions.py
		${SRC_DIR}/compiler/sequents.py
		${SRC_DIR}/compiler/parser.py
		${SRC_DIR}/compiler/compiler.py
		${SRC_DIR}/compiler/cpp.py
		${SRC_DIR}/compiler/run.py
		${SRC_DIR}/laws/group.rules
		${SRC_DIR}/laws/h4.rules
		${SRC_DIR}/laws/h4.facts
	)
add_executable(h4.survey h4.laws.cpp)
target_link_libraries(h4.survey ${POMAGMA_SURVEYOR_MAIN_LIBS})
#install(TARGETS h4.survey DESTINATION ${PROJECT_SOURCE_DIR}/bin)

add_custom_command(
	OUTPUT ${CMAKE_CURRENT_LIST_DIR}/sk.laws.cpp
		${SRC_DIR}/laws/sk.compiled
	COMMAND python ${SRC_DIR}/compiler/run.py compile
		${SRC_DIR}/laws/sk.rules
		${SRC_DIR}/laws/sk.facts
		${SRC_DIR}/laws/order.facts
		cpp_out=${CMAKE_CURRENT_LIST_DIR}/sk.laws.cpp
		laws_out=${SRC_DIR}/laws/sk.compiled
	DEPENDS ${SRC_DIR}/compiler/util.py
		${SRC_DIR}/compiler/expressions.py
		${SRC_DIR}/compiler/sequents.py
		${SRC_DIR}/compiler/parser.py
		${SRC_DIR}/compiler/extensional.py
		${SRC_DIR}/compiler/compiler.py
		${SRC_DIR}/compiler/cpp.py
		${SRC_DIR}/compiler/run.py
		${SRC_DIR}/laws/sk.rules
		${SRC_DIR}/laws/sk.facts
		${SRC_DIR}/laws/order.facts
	)
add_executable(sk.survey sk.laws.cpp)
target_link_libraries(sk.survey ${POMAGMA_SURVEYOR_MAIN_LIBS})
#install(TARGETS sk.survey DESTINATION ${PROJECT_SOURCE_DIR}/bin)

# TODO get types.rules to compile
add_custom_command(
	OUTPUT ${CMAKE_CURRENT_LIST_DIR}/skj.laws.cpp
		${SRC_DIR}/laws/skj.compiled
	COMMAND python ${SRC_DIR}/compiler/run.py compile
		${SRC_DIR}/laws/sk.rules
		${SRC_DIR}/laws/join.rules
		#${SRC_DIR}/laws/types.rules
		${SRC_DIR}/laws/sk.facts
		${SRC_DIR}/laws/order.facts
		${SRC_DIR}/laws/types.facts
		cpp_out=${CMAKE_CURRENT_LIST_DIR}/skj.laws.cpp
		laws_out=${SRC_DIR}/laws/skj.compiled
	DEPENDS ${SRC_DIR}/compiler/util.py
		${SRC_DIR}/compiler/expressions.py
		${SRC_DIR}/compiler/sequents.py
		${SRC_DIR}/compiler/parser.py
		${SRC_DIR}/compiler/extensional.py
		${SRC_DIR}/compiler/compiler.py
		${SRC_DIR}/compiler/cpp.py
		${SRC_DIR}/compiler/run.py
		${SRC_DIR}/laws/sk.rules
		${SRC_DIR}/laws/join.rules
		${SRC_DIR}/laws/types.rules
		${SRC_DIR}/laws/sk.facts
		${SRC_DIR}/laws/order.facts
		${SRC_DIR}/laws/types.facts
	)
add_executable(skj.survey skj.laws.cpp)
target_link_libraries(skj.survey ${POMAGMA_SURVEYOR_MAIN_LIBS})
#install(TARGETS skj.survey DESTINATION ${PROJECT_SOURCE_DIR}/bin)

# TODO get reflect.rules to compile
add_custom_command(
	OUTPUT ${CMAKE_CURRENT_LIST_DIR}/skjo.laws.cpp
		${SRC_DIR}/laws/skjo.compiled
	COMMAND python ${SRC_DIR}/compiler/run.py compile
		${SRC_DIR}/laws/sk.rules
		${SRC_DIR}/laws/join.rules
		#${SRC_DIR}/laws/types.rules
		${SRC_DIR}/laws/quote.rules
		#${SRC_DIR}/laws/reflect.rules
		${SRC_DIR}/laws/sk.facts
		${SRC_DIR}/laws/order.facts
		${SRC_DIR}/laws/types.facts
		${SRC_DIR}/laws/quote.facts
		${SRC_DIR}/laws/reflect.facts
		cpp_out=${CMAKE_CURRENT_LIST_DIR}/skjo.laws.cpp
		laws_out=${SRC_DIR}/laws/skjo.compiled
	DEPENDS ${SRC_DIR}/compiler/util.py
		${SRC_DIR}/compiler/expressions.py
		${SRC_DIR}/compiler/sequents.py
		${SRC_DIR}/compiler/parser.py
		${SRC_DIR}/compiler/extensional.py
		${SRC_DIR}/compiler/compiler.py
		${SRC_DIR}/compiler/cpp.py
		${SRC_DIR}/compiler/run.py
		${SRC_DIR}/laws/sk.rules
		${SRC_DIR}/laws/join.rules
		${SRC_DIR}/laws/types.rules
		${SRC_DIR}/laws/quote.rules
		${SRC_DIR}/laws/reflect.rules
		${SRC_DIR}/laws/sk.facts
		${SRC_DIR}/laws/order.facts
		${SRC_DIR}/laws/types.facts
		${SRC_DIR}/laws/quote.facts
		${SRC_DIR}/laws/reflect.facts
	)
add_executable(skjo.survey skjo.laws.cpp)
target_link_libraries(skjo.survey ${POMAGMA_SURVEYOR_MAIN_LIBS})
#install(TARGETS skjo.survey DESTINATION ${PROJECT_SOURCE_DIR}/bin)

