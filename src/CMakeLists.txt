
set(SRC_DIR ${PROJECT_SOURCE_DIR}/src)
include_directories(${CMAKE_SOURCE_DIR}/)

add_library(pomagma_surveyor SHARED
	util/util.cpp
	util/aligned_alloc.cpp
	util/concurrent_dense_set.cpp
	language/language.pb.cc
	surveyor/carrier.cpp
	surveyor/base_bin_rel.cpp
	surveyor/binary_relation.cpp
	surveyor/nullary_function.cpp
	surveyor/injective_function.cpp
	surveyor/binary_function.cpp
	surveyor/symmetric_function.cpp
	surveyor/parser.cpp
	surveyor/sampler.cpp
	surveyor/structure.cpp
	surveyor/scheduler.cpp
	)
#install(TARGETS pomagma_surveyor LIBRARY DESTINATION ${PROJECT_SOURCE_DIR}/lib)

add_library(pomagma_atlas SHARED
	util/util.cpp
	util/aligned_alloc.cpp
	util/sequential_dense_set.cpp
	language/language.pb.cc
	atlas/carrier.cpp
	atlas/base_bin_rel.cpp
	atlas/binary_relation.cpp
	atlas/nullary_function.cpp
	atlas/injective_function.cpp
	atlas/binary_function.cpp
	atlas/symmetric_function.cpp
	atlas/parser.cpp
	atlas/sampler.cpp
	atlas/structure.cpp
	atlas/scheduler.cpp
	atlas/compact.cpp
	atlas/aggregate.cpp
	atlas/trim.cpp
	)
#install(TARGETS pomagma_atlas LIBRARY DESTINATION ${PROJECT_SOURCE_DIR}/lib)

add_custom_command(
	OUTPUT ${SRC_DIR}/language/language.pb.cc
	COMMAND protoc ${SRC_DIR}/language/language.proto
		--proto_path=${SRC_DIR}/language
		--cpp_out=${CMAKE_CURRENT_LIST_DIR}/language
	DEPENDS ${SRC_DIR}/language/language.proto
	)

#add_custom_command(
#	OUTPUT ${SRC_DIR}/language/language_pb2.py
#	COMMAND protoc ${SRC_DIR}/language/language.proto
#		--proto_path=${SRC_DIR}/language
#		--python_out=${CMAKE_CURRENT_LIST_DIR}/language
#	DEPENDS ${SRC_DIR}/language/language.proto
#	)

add_custom_command(
	OUTPUT ${SRC_DIR}/structure/structure.pb.cc
	COMMAND protoc ${SRC_DIR}/structure/structure.proto
		--proto_path=${SRC_DIR}/structure
		--cpp_out=${CMAKE_CURRENT_LIST_DIR}/structure
	DEPENDS ${SRC_DIR}/structure/structure.proto
	)

add_subdirectory(util)
add_subdirectory(surveyor)
add_subdirectory(atlas)
