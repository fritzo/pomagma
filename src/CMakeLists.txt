include_directories(${CMAKE_SOURCE_DIR}/include)

set(POMAGMA_UTIL_LIBS
	pomagma_util
	pomagma_farmhash
	tbb
	crypto ssl
	${Boost_FILESYSTEM_LIBRARY}
	${Boost_SYSTEM_LIBRARY}
	#tcmalloc  # THIS MUST LINKED LAST
)

set(POMAGMA_IO_LIBS
	pomagma_io
	protobuf
)

set(POMAGMA_WORLD_LIBS
	pomagma_world
	pomagma_atlas
	pomagma_language
	${POMAGMA_IO_LIBS}
	${POMAGMA_UTIL_LIBS}
)

set(POMAGMA_CHART_LIBS
	pomagma_chart
	pomagma_atlas
	pomagma_language
	${POMAGMA_IO_LIBS}
	${POMAGMA_UTIL_LIBS}
)

set(POMAGMA_SHARD_LIBS
	pomagma_shard
	pomagma_atlas
	pomagma_language
	${POMAGMA_IO_LIBS}
	${POMAGMA_UTIL_LIBS}
)

add_subdirectory(util)
add_subdirectory(io)
add_subdirectory(language)
add_subdirectory(atlas)
add_subdirectory(surveyor)
add_subdirectory(cartographer)
add_subdirectory(theorist)
add_subdirectory(analyst)
add_subdirectory(third_party)
