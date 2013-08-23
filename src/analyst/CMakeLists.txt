
include_directories(${CMAKE_SOURCE_DIR}/)

add_library(pomagma_analyst SHARED
	simplify.cpp
	approximate.cpp
	)
set(POMAGMA_THEORIST_LIBS
	pomagma_analyst
	pomagma_macrostructure
	pomagma_platform_sequential
	pomagma_language
	${POMAGMA_SEQUENTIAL_LIBS}
	)

add_executable(simplify simplify_main.cpp)
target_link_libraries(simplify ${POMAGMA_THEORIST_LIBS})

add_executable(serve serve_main.cpp server.cpp)
target_link_libraries(serve ${POMAGMA_THEORIST_LIBS} zmq)
