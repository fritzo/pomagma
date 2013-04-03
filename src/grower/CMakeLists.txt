
include_directories(${CMAKE_SOURCE_DIR}/)

set(POMAGMA_GROWER_LIBS
	pomagma_grower
       	boost_thread
       	tbb
       	hdf5_hl hdf5
	crypto ssl
	protobuf
	)


add_library(pomagma_grower_dummy SHARED dummy.theory.cpp)
set(POMAGMA_GROWER_TEST_LIBS
	pomagma_grower
	pomagma_grower_dummy
	boost_thread
	tbb
       	hdf5_hl hdf5
	crypto ssl
	protobuf
	)

add_executable(grower_carrier_test carrier_test.cpp)
target_link_libraries(grower_carrier_test ${POMAGMA_GROWER_TEST_LIBS})
add_test(NAME grower_carrier COMMAND grower_carrier_test)

add_executable(grower_binary_relation_test binary_relation_test.cpp)
target_link_libraries(grower_binary_relation_test ${POMAGMA_GROWER_TEST_LIBS})
add_test(NAME grower_binary_relation COMMAND grower_binary_relation_test)

add_executable(grower_nullary_function_test nullary_function_test.cpp)
target_link_libraries(grower_nullary_function_test ${POMAGMA_GROWER_TEST_LIBS})
add_test(NAME grower_nullary_function COMMAND grower_nullary_function_test)

add_executable(grower_injective_function_test injective_function_test.cpp)
target_link_libraries(grower_injective_function_test ${POMAGMA_GROWER_TEST_LIBS})
add_test(NAME grower_injective_function COMMAND grower_injective_function_test)

add_executable(grower_binary_function_test binary_function_test.cpp)
target_link_libraries(grower_binary_function_test ${POMAGMA_GROWER_TEST_LIBS})
add_test(NAME grower_binary_function COMMAND grower_binary_function_test)

add_executable(grower_symmetric_function_test symmetric_function_test.cpp)
target_link_libraries(grower_symmetric_function_test ${POMAGMA_GROWER_TEST_LIBS})
add_test(NAME grower_symmetric_function COMMAND grower_symmetric_function_test)

add_executable(grower_scheduler_test scheduler_test.cpp)
target_link_libraries(grower_scheduler_test ${POMAGMA_GROWER_TEST_LIBS})
add_test(NAME grower_scheduler COMMAND grower_scheduler_test)


add_library(pomagma_grower_main SHARED main.cpp)
install(TARGETS pomagma_grower_main LIBRARY
       	DESTINATION ${PROJECT_SOURCE_DIR}/lib
	)
set(POMAGMA_GROWER_MAIN_LIBS
	pomagma_grower_main
	${POMAGMA_GROWER_LIBS}
	#zmq
	)


add_executable(dummy.grow dummy.theory.cpp)
target_link_libraries(dummy.grow ${POMAGMA_GROWER_MAIN_LIBS})

set(SRC_DIR ${PROJECT_SOURCE_DIR}/src)

add_custom_command(
	OUTPUT ${CMAKE_CURRENT_LIST_DIR}/h4.theory.cpp
		${SRC_DIR}/theory/h4.compiled
	COMMAND python ${SRC_DIR}/compiler/run.py compile
		${SRC_DIR}/theory/group.rules
		${SRC_DIR}/theory/h4.rules
		${SRC_DIR}/theory/h4.facts
		cpp_out=${CMAKE_CURRENT_LIST_DIR}/h4.theory.cpp
		theory_out=${SRC_DIR}/theory/h4.compiled
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
add_executable(h4.grow h4.theory.cpp)
target_link_libraries(h4.grow ${POMAGMA_GROWER_MAIN_LIBS})
install(TARGETS h4.grow DESTINATION ${PROJECT_SOURCE_DIR}/bin)

add_custom_command(
	OUTPUT ${CMAKE_CURRENT_LIST_DIR}/sk.theory.cpp
		${SRC_DIR}/theory/sk.compiled
	COMMAND python ${SRC_DIR}/compiler/run.py compile
		${SRC_DIR}/theory/sk.rules
		${SRC_DIR}/theory/sk.facts
		${SRC_DIR}/theory/order.facts
		cpp_out=${CMAKE_CURRENT_LIST_DIR}/sk.theory.cpp
		theory_out=${SRC_DIR}/theory/sk.compiled
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
add_executable(sk.grow sk.theory.cpp)
target_link_libraries(sk.grow ${POMAGMA_GROWER_MAIN_LIBS})
install(TARGETS sk.grow DESTINATION ${PROJECT_SOURCE_DIR}/bin)

# TODO get types.rules to compile
add_custom_command(
	OUTPUT ${CMAKE_CURRENT_LIST_DIR}/skj.theory.cpp
		${SRC_DIR}/theory/skj.compiled
	COMMAND python ${SRC_DIR}/compiler/run.py compile
		${SRC_DIR}/theory/sk.rules
		${SRC_DIR}/theory/join.rules
		#${SRC_DIR}/theory/types.rules
		${SRC_DIR}/theory/sk.facts
		${SRC_DIR}/theory/order.facts
		${SRC_DIR}/theory/types.facts
		cpp_out=${CMAKE_CURRENT_LIST_DIR}/skj.theory.cpp
		theory_out=${SRC_DIR}/theory/skj.compiled
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
		${SRC_DIR}/theory/types.rules
		${SRC_DIR}/theory/sk.facts
		${SRC_DIR}/theory/order.facts
		${SRC_DIR}/theory/types.facts
	)
add_executable(skj.grow skj.theory.cpp)
target_link_libraries(skj.grow ${POMAGMA_GROWER_MAIN_LIBS})
install(TARGETS skj.grow DESTINATION ${PROJECT_SOURCE_DIR}/bin)

# TODO get reflect.rules to compile
add_custom_command(
	OUTPUT ${CMAKE_CURRENT_LIST_DIR}/skjo.theory.cpp
		${SRC_DIR}/theory/skjo.compiled
	COMMAND python ${SRC_DIR}/compiler/run.py compile
		${SRC_DIR}/theory/sk.rules
		${SRC_DIR}/theory/join.rules
		#${SRC_DIR}/theory/types.rules
		${SRC_DIR}/theory/quote.rules
		#${SRC_DIR}/theory/reflect.rules
		${SRC_DIR}/theory/sk.facts
		${SRC_DIR}/theory/order.facts
		${SRC_DIR}/theory/types.facts
		${SRC_DIR}/theory/quote.facts
		${SRC_DIR}/theory/reflect.facts
		cpp_out=${CMAKE_CURRENT_LIST_DIR}/skjo.theory.cpp
		theory_out=${SRC_DIR}/theory/skjo.compiled
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
		${SRC_DIR}/theory/types.rules
		${SRC_DIR}/theory/quote.rules
		${SRC_DIR}/theory/reflect.rules
		${SRC_DIR}/theory/sk.facts
		${SRC_DIR}/theory/order.facts
		${SRC_DIR}/theory/types.facts
		${SRC_DIR}/theory/quote.facts
		${SRC_DIR}/theory/reflect.facts
	)
add_executable(skjo.grow skjo.theory.cpp)
target_link_libraries(skjo.grow ${POMAGMA_GROWER_MAIN_LIBS})
install(TARGETS skjo.grow DESTINATION ${PROJECT_SOURCE_DIR}/bin)

