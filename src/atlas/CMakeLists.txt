include_directories(${CMAKE_SOURCE_DIR}/include)

add_library(pomagma_atlas SHARED
	structure.pb.cc
	program.cpp
)

add_executable(atlas_protobuf_test protobuf_test.cpp)
target_link_libraries(atlas_protobuf_test
	pomagma_atlas
	${POMAGMA_IO_LIBS}
	${POMAGMA_UTIL_LIBS}
)
add_test(NAME atlas_protobuf COMMAND atlas_protobuf_test)

add_subdirectory(micro)
add_subdirectory(macro)
add_subdirectory(shard)
