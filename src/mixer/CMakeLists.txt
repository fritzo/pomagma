
#include_directories(${CMAKE_SOURCE_DIR}/)

add_library(pomagma_mixer SHARED
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
install(TARGETS pomagma_mixer LIBRARY DESTINATION ${PROJECT_SOURCE_DIR}/lib)
set(POMAGMA_LIBS pomagma_mixer boost_thread tbb)


add_library(pomagma_mixer_dummy SHARED dummy.theory.cpp)
set(POMAGMA_TEST_LIBS pomagma_mixer pomagma_mixer_dummy boost_thread tbb)


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


add_library(pomagma_mixer_server SHARED
	server.cpp
	)
install(TARGETS pomagma_mixer_server LIBRARY
       	DESTINATION ${PROJECT_SOURCE_DIR}/lib
	)
set(POMAGMA_SERVER_LIBS pomagma_mixer_server ${POMAGMA_LIBS} zmq)


add_executable(dummy.mixer dummy.theory.cpp)
target_link_libraries(dummy.mixer ${POMAGMA_SERVER_LIBS})

set(COMPILER_DIR ${PROJECT_SOURCE_DIR}/src/compiler)

# TODO abstract these out as functions
add_custom_command(
	OUTPUT ${CMAKE_CURRENT_LIST_DIR}/sk.theory.cpp
	COMMAND python ${COMPILER_DIR}/run.py compile
		${COMPILER_DIR}/sk.rules
		outfile=${CMAKE_CURRENT_LIST_DIR}/sk.theory.cpp
	DEPENDS ${COMPILER_DIR}/util.py
		${COMPILER_DIR}/expressions.py
		${COMPILER_DIR}/sequents.py
		${COMPILER_DIR}/parser.py
		${COMPILER_DIR}/compiler.py
		${COMPILER_DIR}/cpp.py
		${COMPILER_DIR}/run.py
		${COMPILER_DIR}/sk.rules
	)
add_executable(sk.mixer sk.theory.cpp)
target_link_libraries(sk.mixer ${POMAGMA_SERVER_LIBS})
install(TARGETS sk.mixer DESTINATION ${PROJECT_SOURCE_DIR}/bin)

add_custom_command(
	OUTPUT ${CMAKE_CURRENT_LIST_DIR}/skj.theory.cpp
	COMMAND python ${COMPILER_DIR}/run.py compile
		${COMPILER_DIR}/sk.rules
		${COMPILER_DIR}/join.rules
		outfile=${CMAKE_CURRENT_LIST_DIR}/skj.theory.cpp
	DEPENDS ${COMPILER_DIR}/util.py
		${COMPILER_DIR}/expressions.py
		${COMPILER_DIR}/sequents.py
		${COMPILER_DIR}/parser.py
		${COMPILER_DIR}/compiler.py
		${COMPILER_DIR}/cpp.py
		${COMPILER_DIR}/run.py
		${COMPILER_DIR}/sk.rules
		${COMPILER_DIR}/join.rules
	)
# TODO get skj.theory.cpp to compile
#add_executable(skj.mixer skj.theory.cpp)
#target_link_libraries(skj.mixer ${POMAGMA_SERVER_LIBS})
#install(TARGETS skj.mixer DESTINATION ${PROJECT_SOURCE_DIR}/bin)
