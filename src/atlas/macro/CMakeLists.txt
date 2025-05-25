include_directories(${CMAKE_SOURCE_DIR}/include)

add_library(pomagma_world SHARED
	carrier.cpp
	base_bin_rel.cpp
	unary_relation.cpp
	binary_relation.cpp
	nullary_function.cpp
	injective_function.cpp
	binary_function.cpp
	symmetric_function.cpp
	sampler.cpp
	structure.cpp
	scheduler.cpp
	vm.cpp
	compact.cpp
	router.cpp
)
target_link_libraries(pomagma_world 
	pomagma_atlas
	pomagma_language
	${POMAGMA_IO_LIBS}
	${POMAGMA_UTIL_LIBS}
)

pomagma_add_executable(world_carrier_test carrier_test.cpp)
target_link_libraries(world_carrier_test ${POMAGMA_WORLD_LIBS})
add_test(NAME atlas_world_carrier COMMAND world_carrier_test)

pomagma_add_executable(world_unary_relation_test unary_relation_test.cpp)
target_link_libraries(world_unary_relation_test ${POMAGMA_WORLD_LIBS})
add_test(NAME atlas_world_unary_relation COMMAND world_unary_relation_test)

pomagma_add_executable(world_binary_relation_test binary_relation_test.cpp)
target_link_libraries(world_binary_relation_test ${POMAGMA_WORLD_LIBS})
add_test(NAME atlas_world_binary_relation COMMAND world_binary_relation_test)

pomagma_add_executable(world_nullary_function_test nullary_function_test.cpp)
target_link_libraries(world_nullary_function_test ${POMAGMA_WORLD_LIBS})
add_test(NAME atlas_world_nullary_function COMMAND world_nullary_function_test)

pomagma_add_executable(world_injective_function_test injective_function_test.cpp)
target_link_libraries(world_injective_function_test ${POMAGMA_WORLD_LIBS})
add_test(NAME atlas_world_injective_function COMMAND world_injective_function_test)

pomagma_add_executable(world_binary_function_test binary_function_test.cpp)
target_link_libraries(world_binary_function_test ${POMAGMA_WORLD_LIBS})
add_test(NAME atlas_world_binary_function COMMAND world_binary_function_test)

pomagma_add_executable(world_symmetric_function_test symmetric_function_test.cpp)
target_link_libraries(world_symmetric_function_test ${POMAGMA_WORLD_LIBS})
add_test(NAME atlas_world_symmetric_function COMMAND world_symmetric_function_test)
