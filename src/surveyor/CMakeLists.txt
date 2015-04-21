include_directories(${CMAKE_SOURCE_DIR}/include)

add_library(pomagma_surveyor SHARED
       	vm.cpp
	cleanup.cpp)

set(POMAGMA_SURVEYOR_LIBS
	pomagma_microstructure
	pomagma_platform_concurrent
	pomagma_language
	pomagma_surveyor
	${POMAGMA_CONCURRENT_LIBS}
)

add_library(pomagma_surveyor_vm SHARED theory.cpp)
add_executable(init init_main.cpp)
target_link_libraries(init
	pomagma_surveyor_vm
	${POMAGMA_SURVEYOR_LIBS})
add_executable(survey survey_main.cpp)
target_link_libraries(survey
	pomagma_surveyor_vm
	${POMAGMA_SURVEYOR_LIBS})

function(make_surveyor arg)
	add_library(pomagma_surveyor_${arg} SHARED ${arg}.theory.cpp)
	add_executable(${arg}.init init_main.cpp)
	target_link_libraries(${arg}.init
		pomagma_surveyor_${arg}
		${POMAGMA_SURVEYOR_LIBS})
	add_executable(${arg}.survey survey_main.cpp)
	target_link_libraries(${arg}.survey
		pomagma_surveyor_${arg}
		${POMAGMA_SURVEYOR_LIBS})
endfunction()

make_surveyor(h4)
make_surveyor(sk)
make_surveyor(skj)
make_surveyor(skja)
make_surveyor(skrj)
make_surveyor(skjo)
