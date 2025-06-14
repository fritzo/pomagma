include_directories(${CMAKE_SOURCE_DIR})

set(POMAGMA_UTIL_LIBS
	pomagma_util
	pomagma_farmhash
	TBB::tbb
	OpenSSL::Crypto OpenSSL::SSL
	#tcmalloc  # THIS MUST LINKED LAST
)

set(POMAGMA_IO_LIBS
	pomagma_io
	protobuf::libprotobuf
	ZLIB::ZLIB
	absl::log
	absl::absl_log
	absl::log_internal_message
	absl::log_internal_check_op
	absl::log_internal_format
	absl::log_internal_log_impl
	absl::log_streamer
	absl::base
	absl::strings
	absl::str_format
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

add_subdirectory(analyst)
add_subdirectory(atlas)
add_subdirectory(cartographer)
add_subdirectory(io)
add_subdirectory(language)
add_subdirectory(solver)
add_subdirectory(surveyor)
add_subdirectory(torch)
add_subdirectory(theorist)
add_subdirectory(third_party)
add_subdirectory(util)
