
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

add_library(pomagma_cartographer SHARED
	util/util.cpp
	util/aligned_alloc.cpp
	util/sequential_dense_set.cpp
	language/language.pb.cc
	cartographer/carrier.cpp
	cartographer/base_bin_rel.cpp
	cartographer/binary_relation.cpp
	cartographer/nullary_function.cpp
	cartographer/injective_function.cpp
	cartographer/binary_function.cpp
	cartographer/symmetric_function.cpp
	cartographer/parser.cpp
	cartographer/sampler.cpp
	cartographer/structure.cpp
	cartographer/scheduler.cpp
	cartographer/compact.cpp
	cartographer/aggregate.cpp
	cartographer/trim.cpp
	cartographer/conjecture.cpp
	)

add_custom_command(
	OUTPUT ${SRC_DIR}/language/language.pb.cc
	COMMAND protoc ${SRC_DIR}/language/language.proto
		--proto_path=${SRC_DIR}/language
		--cpp_out=${CMAKE_CURRENT_LIST_DIR}/language
	DEPENDS ${SRC_DIR}/language/language.proto
	)

add_subdirectory(util)
add_subdirectory(surveyor)
add_subdirectory(cartographer)
