
include_directories(${CMAKE_SOURCE_DIR}/)

add_library(pomagma_cartographer SHARED
	aggregate.cpp
	trim.cpp
	hypothesize.cpp
	conjecture.cpp
	)
set(POMAGMA_CARTOGRAPHER_LIBS
	pomagma_cartographer
	pomagma_macrostructure
	pomagma_platform_sequential
       	hdf5_hl hdf5
	crypto ssl
	protobuf
	)

add_executable(copy copy_main.cpp)
target_link_libraries(copy ${POMAGMA_CARTOGRAPHER_LIBS})

add_executable(aggregate aggregate_main.cpp)
target_link_libraries(aggregate ${POMAGMA_CARTOGRAPHER_LIBS})

add_executable(trim trim_main.cpp)
target_link_libraries(trim ${POMAGMA_CARTOGRAPHER_LIBS})

add_executable(conjecture conjecture_main.cpp)
target_link_libraries(conjecture ${POMAGMA_CARTOGRAPHER_LIBS})

