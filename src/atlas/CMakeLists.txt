include_directories(${CMAKE_SOURCE_DIR}/include)

add_library(pomagma_structure_micro SHARED
	messages.pb.cc
)

add_library(pomagma_structure_macro SHARED
	messages.pb.cc
)

#add_subdirectory(macro)
#add_subdirectory(micro)
