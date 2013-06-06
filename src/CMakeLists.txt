
set(SRC_DIR ${PROJECT_SOURCE_DIR}/src)
include_directories(${CMAKE_SOURCE_DIR}/)

add_library(pomagma_platform_sequential SHARED
	platform/util.cpp
	platform/aligned_alloc.cpp
	platform/sequential_dense_set.cpp
	platform/language.cpp
	language/language.pb.cc
	)

add_library(pomagma_platform_concurrent SHARED
	platform/util.cpp
	platform/aligned_alloc.cpp
	platform/concurrent_dense_set.cpp
	platform/language.cpp
	language/language.pb.cc
	)

add_custom_command(
	OUTPUT ${SRC_DIR}/language/language.pb.cc
	COMMAND protoc ${SRC_DIR}/language/language.proto
		--proto_path=${SRC_DIR}/language
		--cpp_out=${CMAKE_CURRENT_LIST_DIR}/language
	DEPENDS ${SRC_DIR}/language/language.proto
	)

set(POMAGMA_SEQUENTIAL_LIBS
       	hdf5_hl hdf5
	crypto ssl
	protobuf
	)

set(POMAGMA_CONCURRENT_LIBS
       	boost_thread
       	tbb
       	hdf5_hl hdf5
	crypto ssl
	protobuf
	)

add_subdirectory(platform)
add_subdirectory(macrostructure)
add_subdirectory(surveyor)
add_subdirectory(cartographer)
add_subdirectory(theorist)
