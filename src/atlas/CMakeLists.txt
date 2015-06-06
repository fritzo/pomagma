include_directories(${CMAKE_SOURCE_DIR}/include)

add_library(pomagma_structure_micro SHARED
	messages.pb.cc
)

add_library(pomagma_structure_macro SHARED
	messages.pb.cc
)

add_executable(atlas_protobuf_test protobuf_test.cpp)
target_link_libraries(atlas_protobuf_test
    pomagma_structure_macro
    ${POMAGMA_UTIL_LIBS})
add_test(NAME atlas_protobuf COMMAND atlas_protobuf_test)

#add_subdirectory(macro)
#add_subdirectory(micro)
