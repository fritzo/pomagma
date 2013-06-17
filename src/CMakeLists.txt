
include_directories(${CMAKE_SOURCE_DIR}/)

set(POMAGMA_SEQUENTIAL_LIBS
       	hdf5_hl hdf5
	crypto ssl
	protobuf
	)

set(POMAGMA_CONCURRENT_LIBS
       	boost_thread
       	tbb
       	hdf5_hl hdf5
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
