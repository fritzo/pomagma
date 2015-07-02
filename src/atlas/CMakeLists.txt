include_directories(${CMAKE_SOURCE_DIR}/include)

add_library(pomagma_atlas_chart SHARED structure.pb.cc)
add_library(pomagma_atlas_world SHARED structure.pb.cc)

add_executable(atlas_protobuf_test protobuf_test.cpp)
target_link_libraries(atlas_protobuf_test
	pomagma_atlas_world
	${POMAGMA_IO_LIBS}
	${POMAGMA_UTIL_LIBS}
)
add_test(NAME atlas_protobuf COMMAND atlas_protobuf_test)

add_subdirectory(chart)
add_subdirectory(world)
