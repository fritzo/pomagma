
include_directories(${CMAKE_SOURCE_DIR}/)

add_library(pomagma_cartographer SHARED
	signature.cpp
	aggregate.cpp
	trim.cpp
	)
set(POMAGMA_CARTOGRAPHER_LIBS
	pomagma_cartographer
	pomagma_macrostructure
	pomagma_platform_sequential
	pomagma_language
	${POMAGMA_SEQUENTIAL_LIBS})

add_executable(validate validate_main.cpp)
target_link_libraries(validate ${POMAGMA_CARTOGRAPHER_LIBS})

add_executable(copy copy_main.cpp)
target_link_libraries(copy ${POMAGMA_CARTOGRAPHER_LIBS})

add_executable(aggregate aggregate_main.cpp)
target_link_libraries(aggregate ${POMAGMA_CARTOGRAPHER_LIBS})

add_executable(trim trim_main.cpp)
target_link_libraries(trim ${POMAGMA_CARTOGRAPHER_LIBS})

