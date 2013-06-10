
include_directories(${CMAKE_SOURCE_DIR}/)

add_library(pomagma_macrostructure SHARED
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
	compact.cpp
	router.cpp
	)
set(POMAGMA_MACROSTRUCTURE_LIBS
	pomagma_macrostructure
	pomagma_platform_sequential
	pomagma_language
	${POMAGMA_SEQUENTIAL_LIBS})

add_executable(macrostructure_carrier_test carrier_test.cpp)
target_link_libraries(macrostructure_carrier_test
	${POMAGMA_MACROSTRUCTURE_LIBS})
add_test(NAME macrostructure_carrier COMMAND macrostructure_carrier_test)

add_executable(binary_relation_test binary_relation_test.cpp)
target_link_libraries(binary_relation_test ${POMAGMA_MACROSTRUCTURE_LIBS})
add_test(NAME macrostructure_binary_relation COMMAND binary_relation_test)

add_executable(nullary_function_test nullary_function_test.cpp)
target_link_libraries(nullary_function_test ${POMAGMA_MACROSTRUCTURE_LIBS})
add_test(NAME macrostructure_nullary_function COMMAND nullary_function_test)

add_executable(injective_function_test injective_function_test.cpp)
target_link_libraries(injective_function_test ${POMAGMA_MACROSTRUCTURE_LIBS})
add_test(NAME macrostructure_injective_function COMMAND injective_function_test)

add_executable(binary_function_test binary_function_test.cpp)
target_link_libraries(binary_function_test ${POMAGMA_MACROSTRUCTURE_LIBS})
add_test(NAME macrostructure_binary_function COMMAND binary_function_test)

add_executable(symmetric_function_test symmetric_function_test.cpp)
target_link_libraries(symmetric_function_test ${POMAGMA_MACROSTRUCTURE_LIBS})
add_test(NAME macrostructure_symmetric_function COMMAND symmetric_function_test)

