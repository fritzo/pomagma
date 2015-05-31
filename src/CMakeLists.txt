include_directories(${CMAKE_SOURCE_DIR}/include)

set(POMAGMA_SEQUENTIAL_LIBS
	tbb
	hdf5 hdf5_hl
	crypto ssl
	protobuf
)

set(POMAGMA_CONCURRENT_LIBS
	tbb
	hdf5 hdf5_hl
	crypto ssl
	protobuf
)

set(POMAGMA_MACROSTRUCTURE_LIBS
	pomagma_macrostructure
	pomagma_structure_macro
	pomagma_language
	pomagma_platform_sequential
	${POMAGMA_SEQUENTIAL_LIBS}
)

set(POMAGMA_MICROSTRUCTURE_LIBS
	pomagma_microstructure
	pomagma_structure_micro
	pomagma_language
	pomagma_platform_concurrent
	${POMAGMA_CONCURRENT_LIBS}
)

add_subdirectory(platform)
add_subdirectory(language)
add_subdirectory(structure)
add_subdirectory(microstructure)
add_subdirectory(macrostructure)
add_subdirectory(surveyor)
add_subdirectory(cartographer)
add_subdirectory(theorist)
add_subdirectory(analyst)
add_subdirectory(protobuf)
