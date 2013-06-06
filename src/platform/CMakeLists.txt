
include_directories(${CMAKE_SOURCE_DIR}/)

add_executable(threading_profile threading_profile.cpp)
target_link_libraries(threading_profile
	pomagma_platform_concurrent
       	${POMAGMA_CONCURRENT_LIBS})

add_subdirectory(concurrent)
add_subdirectory(sequential)
