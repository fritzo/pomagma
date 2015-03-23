include_directories(${CMAKE_SOURCE_DIR}/include)


set(POMAGMA_SURVEYOR_LIBS
	pomagma_microstructure
	pomagma_platform_concurrent
	pomagma_language
	${POMAGMA_CONCURRENT_LIBS}
)


set(SRC_DIR ${PROJECT_SOURCE_DIR}/src)

set(POMAGMA_COMPILER_FILES
	${SRC_DIR}/compiler/util.py
	${SRC_DIR}/compiler/expressions.py
	${SRC_DIR}/compiler/sequents.py
	${SRC_DIR}/compiler/parser.py
	${SRC_DIR}/compiler/compiler.py
	${SRC_DIR}/compiler/cpp.py
	${SRC_DIR}/compiler/__main__.py
)

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
add_custom_command(
	OUTPUT ${CMAKE_CURRENT_LIST_DIR}/h4.theory.cpp
		${SRC_DIR}/theory/h4.compiled
	WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
	COMMAND python -m pomagma.compiler compile
		${SRC_DIR}/theory/group.rules
		${SRC_DIR}/theory/h4.rules
		${SRC_DIR}/theory/h4.facts
		cpp_out=${CMAKE_CURRENT_LIST_DIR}/h4.theory.cpp
		theory_out=${SRC_DIR}/theory/h4.compiled
		extensional=false
	DEPENDS ${POMAGMA_COMPILER_FILES}
		${SRC_DIR}/theory/group.rules
		${SRC_DIR}/theory/h4.rules
		${SRC_DIR}/theory/h4.facts
)

make_surveyor(sk)
add_custom_command(
	OUTPUT ${CMAKE_CURRENT_LIST_DIR}/sk.theory.cpp
		${SRC_DIR}/theory/sk.compiled
	WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
	COMMAND python -m pomagma.compiler compile
		${SRC_DIR}/theory/sk.rules
		${SRC_DIR}/theory/order.rules
		${SRC_DIR}/theory/sk.facts
		${SRC_DIR}/theory/order.facts
		cpp_out=${CMAKE_CURRENT_LIST_DIR}/sk.theory.cpp
		theory_out=${SRC_DIR}/theory/sk.compiled
	DEPENDS ${POMAGMA_COMPILER_FILES}
		${SRC_DIR}/theory/sk.rules
		${SRC_DIR}/theory/order.rules
		${SRC_DIR}/theory/sk.facts
		${SRC_DIR}/theory/order.facts
)

make_surveyor(skj)
add_custom_command(
	OUTPUT ${CMAKE_CURRENT_LIST_DIR}/skj.theory.cpp
		${SRC_DIR}/theory/skj.compiled
	WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
	COMMAND python -m pomagma.compiler compile
		${SRC_DIR}/theory/sk.rules
		${SRC_DIR}/theory/order.rules
		${SRC_DIR}/theory/join.rules
		${SRC_DIR}/theory/closures.rules
		${SRC_DIR}/theory/types.rules
		${SRC_DIR}/theory/a.rules
		${SRC_DIR}/theory/sk.facts
		${SRC_DIR}/theory/order.facts
		${SRC_DIR}/theory/closures.facts
		${SRC_DIR}/theory/types.facts
		${SRC_DIR}/theory/a.facts
		cpp_out=${CMAKE_CURRENT_LIST_DIR}/skj.theory.cpp
		theory_out=${SRC_DIR}/theory/skj.compiled
	DEPENDS ${POMAGMA_COMPILER_FILES}
		${SRC_DIR}/theory/sk.rules
		${SRC_DIR}/theory/order.rules
		${SRC_DIR}/theory/join.rules
		${SRC_DIR}/theory/closures.rules
		${SRC_DIR}/theory/types.rules
		${SRC_DIR}/theory/a.rules
		${SRC_DIR}/theory/sk.facts
		${SRC_DIR}/theory/order.facts
		${SRC_DIR}/theory/closures.facts
		${SRC_DIR}/theory/types.facts
		${SRC_DIR}/theory/a.facts
)

make_surveyor(skrj)
add_custom_command(
	OUTPUT ${CMAKE_CURRENT_LIST_DIR}/skrj.theory.cpp
		${SRC_DIR}/theory/skrj.compiled
	WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
	COMMAND python -m pomagma.compiler compile
		${SRC_DIR}/theory/sk.rules
		${SRC_DIR}/theory/order.rules
		${SRC_DIR}/theory/join.rules
		${SRC_DIR}/theory/rand.rules
		${SRC_DIR}/theory/closures.rules
		${SRC_DIR}/theory/a.rules
		${SRC_DIR}/theory/sk.facts
		${SRC_DIR}/theory/order.facts
		${SRC_DIR}/theory/closures.facts
		${SRC_DIR}/theory/a.facts
		cpp_out=${CMAKE_CURRENT_LIST_DIR}/skrj.theory.cpp
		theory_out=${SRC_DIR}/theory/skrj.compiled
	DEPENDS ${POMAGMA_COMPILER_FILES}
		${SRC_DIR}/theory/sk.rules
		${SRC_DIR}/theory/order.rules
		${SRC_DIR}/theory/join.rules
		${SRC_DIR}/theory/rand.rules
		${SRC_DIR}/theory/closures.rules
		${SRC_DIR}/theory/a.rules
		${SRC_DIR}/theory/sk.facts
		${SRC_DIR}/theory/order.facts
		${SRC_DIR}/theory/closures.facts
		${SRC_DIR}/theory/a.facts
)

make_surveyor(skjo)
add_custom_command(
	OUTPUT ${CMAKE_CURRENT_LIST_DIR}/skjo.theory.cpp
		${SRC_DIR}/theory/skjo.compiled
	WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
	COMMAND python -m pomagma.compiler compile
		${SRC_DIR}/theory/sk.rules
		${SRC_DIR}/theory/order.rules
		${SRC_DIR}/theory/join.rules
		${SRC_DIR}/theory/closures.rules
		${SRC_DIR}/theory/types.rules
		${SRC_DIR}/theory/a.rules
		${SRC_DIR}/theory/quote.rules
		${SRC_DIR}/theory/reflect.rules
		${SRC_DIR}/theory/sk.facts
		${SRC_DIR}/theory/order.facts
		${SRC_DIR}/theory/closures.facts
		${SRC_DIR}/theory/types.facts
		${SRC_DIR}/theory/a.facts
		${SRC_DIR}/theory/quote.facts
		${SRC_DIR}/theory/reflect.facts
		cpp_out=${CMAKE_CURRENT_LIST_DIR}/skjo.theory.cpp
		theory_out=${SRC_DIR}/theory/skjo.compiled
	DEPENDS ${POMAGMA_COMPILER_FILES}
		${SRC_DIR}/theory/sk.rules
		${SRC_DIR}/theory/order.rules
		${SRC_DIR}/theory/join.rules
		${SRC_DIR}/theory/closures.rules
		${SRC_DIR}/theory/types.rules
		${SRC_DIR}/theory/a.rules
		${SRC_DIR}/theory/quote.rules
		${SRC_DIR}/theory/reflect.rules
		${SRC_DIR}/theory/sk.facts
		${SRC_DIR}/theory/order.facts
		${SRC_DIR}/theory/closures.facts
		${SRC_DIR}/theory/types.facts
		${SRC_DIR}/theory/a.facts
		${SRC_DIR}/theory/quote.facts
		${SRC_DIR}/theory/reflect.facts
)
