
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
	scheduler.cpp
	)
#install(TARGETS pomagma_mixer LIBRARY DESTINATION ${PROJECT_SOURCE_DIR}/lib)
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


add_library(pomagma_server SHARED
	server.cpp
	)
#install(TARGETS pomagma_server LIBRARY DESTINATION ${PROJECT_SOURCE_DIR}/lib)
set(POMAGMA_SERVER_LIBS pomagma_server ${POMAGMA_LIBS} zmq)


add_executable(dummy.server dummy.theory.cpp)
target_link_libraries(dummy.server ${POMAGMA_SERVER_LIBS})

# TODO abstract these out as functions
add_custom_command(
	OUTPUT ${CMAKE_CURRENT_LIST_DIR}/sk.theory.cpp
	COMMAND python ${PROJECT_SOURCE_DIR}/pomagma/run.py compile
		${PROJECT_SOURCE_DIR}/pomagma/sk.rules
		outfile=${CMAKE_CURRENT_LIST_DIR}/sk.theory.cpp
	DEPENDS ${PROJECT_SOURCE_DIR}/pomagma/util.py
		${PROJECT_SOURCE_DIR}/pomagma/expressions.py
		${PROJECT_SOURCE_DIR}/pomagma/sequents.py
		${PROJECT_SOURCE_DIR}/pomagma/parser.py
		${PROJECT_SOURCE_DIR}/pomagma/compiler.py
		${PROJECT_SOURCE_DIR}/pomagma/cpp.py
		${PROJECT_SOURCE_DIR}/pomagma/run.py
		${PROJECT_SOURCE_DIR}/pomagma/sk.rules
	)
add_executable(sk.server sk.theory.cpp)
target_link_libraries(sk.server ${POMAGMA_SERVER_LIBS})

add_custom_command(
	OUTPUT ${CMAKE_CURRENT_LIST_DIR}/skj.theory.cpp
	COMMAND python ${PROJECT_SOURCE_DIR}/pomagma/run.py compile
		${PROJECT_SOURCE_DIR}/pomagma/sk.rules
		${PROJECT_SOURCE_DIR}/pomagma/join.rules
		outfile=${CMAKE_CURRENT_LIST_DIR}/skj.theory.cpp
	DEPENDS ${PROJECT_SOURCE_DIR}/pomagma/util.py
		${PROJECT_SOURCE_DIR}/pomagma/expressions.py
		${PROJECT_SOURCE_DIR}/pomagma/sequents.py
		${PROJECT_SOURCE_DIR}/pomagma/parser.py
		${PROJECT_SOURCE_DIR}/pomagma/compiler.py
		${PROJECT_SOURCE_DIR}/pomagma/cpp.py
		${PROJECT_SOURCE_DIR}/pomagma/run.py
		${PROJECT_SOURCE_DIR}/pomagma/sk.rules
		${PROJECT_SOURCE_DIR}/pomagma/join.rules
	)
# TODO get skj.theory.cpp to compile
#add_executable(skj.server skj.theory.cpp)
#target_link_libraries(skj.server ${POMAGMA_SERVER_LIBS})
