
set(SRC_DIR ${PROJECT_SOURCE_DIR}/src)
include_directories(${CMAKE_SOURCE_DIR}/)

add_library(pomagma_util_sequential SHARED
	util/util.cpp
	util/aligned_alloc.cpp
	util/sequential_dense_set.cpp
	util/language.cpp
	language/language.pb.cc
	)

add_library(pomagma_util_concurrent SHARED
	util/util.cpp
	util/aligned_alloc.cpp
	util/concurrent_dense_set.cpp
	util/language.cpp
	language/language.pb.cc
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
