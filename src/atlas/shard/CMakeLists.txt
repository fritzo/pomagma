include_directories(${CMAKE_SOURCE_DIR}/include)

add_library(pomagma_shard SHARED
	index.cpp
	carrier.cpp
	#base_bin_rel.cpp
	#unary_relation.cpp
	#binary_relation.cpp
	#nullary_function.cpp
	#injective_function.cpp
	binary_function.cpp
	#symmetric_function.cpp
	#sampler.cpp
	#structure.cpp
	#scheduler.cpp
	#vm.cpp
	#compact.cpp
	#router.cpp
)
target_link_libraries(pomagma_shard 
	pomagma_atlas
	pomagma_language
	${POMAGMA_IO_LIBS}
	${POMAGMA_UTIL_LIBS}
)

add_executable(shard_carrier_test carrier_test.cpp)
target_link_libraries(shard_carrier_test ${POMAGMA_SHARD_LIBS})
add_test(NAME shard_carrier COMMAND shard_carrier_test)

#add_executable(shard_unary_relation_test unary_relation_test.cpp)
#target_link_libraries(shard_unary_relation_test ${POMAGMA_SHARD_LIBS})
#add_test(NAME shard_unary_relation COMMAND shard_unary_relation_test)
#
#add_executable(shard_binary_relation_test binary_relation_test.cpp)
#target_link_libraries(shard_binary_relation_test ${POMAGMA_SHARD_LIBS})
#add_test(NAME shard_binary_relation COMMAND shard_binary_relation_test)
#
#add_executable(shard_nullary_function_test nullary_function_test.cpp)
#target_link_libraries(shard_nullary_function_test ${POMAGMA_SHARD_LIBS})
#add_test(NAME shard_nullary_function COMMAND shard_nullary_function_test)
#
#add_executable(shard_injective_function_test injective_function_test.cpp)
#target_link_libraries(shard_injective_function_test ${POMAGMA_SHARD_LIBS})
#add_test(NAME shard_injective_function COMMAND shard_injective_function_test)
#
#add_executable(shard_binary_function_test binary_function_test.cpp)
#target_link_libraries(shard_binary_function_test ${POMAGMA_SHARD_LIBS})
#add_test(NAME shard_binary_function COMMAND shard_binary_function_test)
#
#add_executable(shard_symmetric_function_test symmetric_function_test.cpp)
#target_link_libraries(shard_symmetric_function_test ${POMAGMA_SHARD_LIBS})
#add_test(NAME shard_symmetric_function COMMAND shard_symmetric_function_test)
