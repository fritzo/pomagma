
#include_directories(${CMAKE_SOURCE_DIR}/)

add_library(pomagma_engine SHARED
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
	scheduler.cpp
	)
install(TARGETS pomagma_engine LIBRARY DESTINATION ${PROJECT_SOURCE_DIR}/lib)
set(POMAGMA_LIBS pomagma_engine boost_thread tbb)


add_library(pomagma_engine_dummy SHARED dummy.theory.cpp)
set(POMAGMA_TEST_LIBS pomagma_engine pomagma_engine_dummy boost_thread tbb)


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


add_library(pomagma_engine_server SHARED
	server.cpp
	)
install(TARGETS pomagma_engine_server LIBRARY
       	DESTINATION ${PROJECT_SOURCE_DIR}/lib
	)
set(POMAGMA_SERVER_LIBS pomagma_engine_server ${POMAGMA_LIBS} zmq)


add_executable(dummy.engine dummy.theory.cpp)
target_link_libraries(dummy.engine ${POMAGMA_SERVER_LIBS})

set(COMPILER_DIR ${PROJECT_SOURCE_DIR}/src/compiler)
set(THEORY_DIR ${PROJECT_SOURCE_DIR}/src/theory)

# TODO abstract these out as functions
add_custom_command(
	OUTPUT ${CMAKE_CURRENT_LIST_DIR}/sk.theory.cpp
	COMMAND python ${COMPILER_DIR}/run.py compile
	${THEORY_DIR}/sk.rules
		outfile=${CMAKE_CURRENT_LIST_DIR}/sk.theory.cpp
	DEPENDS ${COMPILER_DIR}/util.py
		${COMPILER_DIR}/expressions.py
		${COMPILER_DIR}/sequents.py
		${COMPILER_DIR}/parser.py
		${COMPILER_DIR}/compiler.py
		${COMPILER_DIR}/cpp.py
		${COMPILER_DIR}/run.py
		${THEORY_DIR}/sk.rules
	)
add_executable(sk.engine sk.theory.cpp)
target_link_libraries(sk.engine ${POMAGMA_SERVER_LIBS})
install(TARGETS sk.engine DESTINATION ${PROJECT_SOURCE_DIR}/bin)

add_custom_command(
	OUTPUT ${CMAKE_CURRENT_LIST_DIR}/skj.theory.cpp
	COMMAND python ${COMPILER_DIR}/run.py compile
		${THEORY_DIR}/sk.rules
		${THEORY_DIR}/join.rules
		outfile=${CMAKE_CURRENT_LIST_DIR}/skj.theory.cpp
	DEPENDS ${COMPILER_DIR}/util.py
		${COMPILER_DIR}/expressions.py
		${COMPILER_DIR}/sequents.py
		${COMPILER_DIR}/parser.py
		${COMPILER_DIR}/compiler.py
		${COMPILER_DIR}/cpp.py
		${COMPILER_DIR}/run.py
		${THEORY_DIR}/sk.rules
		${THEORY_DIR}/join.rules
	)
# TODO get skj.theory.cpp to compile
#add_executable(skj.engine skj.theory.cpp)
#target_link_libraries(skj.engine ${POMAGMA_SERVER_LIBS})
#install(TARGETS skj.engine DESTINATION ${PROJECT_SOURCE_DIR}/bin)
