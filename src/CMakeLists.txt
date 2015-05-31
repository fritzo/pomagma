include_directories(${CMAKE_SOURCE_DIR}/include)

set(POMAGMA_SEQUENTIAL_LIBS
	tbb
	hdf5
	hdf5_hl
	crypto ssl
	protobuf
)

set(POMAGMA_CONCURRENT_LIBS
	tbb
	hdf5
	hdf5_hl
	crypto ssl
	protobuf
)

add_subdirectory(platform)
add_subdirectory(language)
add_subdirectory(microstructure)
add_subdirectory(macrostructure)
add_subdirectory(surveyor)
add_subdirectory(cartographer)
add_subdirectory(theorist)
add_subdirectory(analyst)
add_subdirectory(protobuf)
