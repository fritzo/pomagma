include_directories(${CMAKE_SOURCE_DIR}/include)

set(POMAGMA_UTIL_LIBS
	pomagma_util
	tbb
	crypto ssl
	${Boost_FILESYSTEM_LIBRARY}
	${Boost_SYSTEM_LIBRARY}
)

set(POMAGMA_IO_LIBS
	pomagma_io
	hdf5 hdf5_hl
	protobuf
)

set(POMAGMA_MACROSTRUCTURE_LIBS
	pomagma_macrostructure
	pomagma_structure_macro
	pomagma_language
	${POMAGMA_IO_LIBS}
	${POMAGMA_UTIL_LIBS}
)

set(POMAGMA_MICROSTRUCTURE_LIBS
	pomagma_microstructure
	pomagma_structure_micro
	pomagma_language
	${POMAGMA_IO_LIBS}
	${POMAGMA_UTIL_LIBS}
)

add_subdirectory(util)
add_subdirectory(io)
add_subdirectory(language)
add_subdirectory(atlas)
add_subdirectory(microstructure)
add_subdirectory(macrostructure)
add_subdirectory(surveyor)
add_subdirectory(cartographer)
add_subdirectory(theorist)
add_subdirectory(analyst)
