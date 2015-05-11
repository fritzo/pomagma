include_directories(${CMAKE_SOURCE_DIR}/include)

add_library(pomagma_surveyor SHARED
       	vm.cpp
       	theory.cpp)

set(POMAGMA_SURVEYOR_LIBS
	pomagma_microstructure
	pomagma_platform_concurrent
	pomagma_language
	pomagma_surveyor
	${POMAGMA_CONCURRENT_LIBS}
)

add_executable(init init_main.cpp)
target_link_libraries(init ${POMAGMA_SURVEYOR_LIBS})

add_executable(survey survey_main.cpp)
target_link_libraries(survey ${POMAGMA_SURVEYOR_LIBS})
