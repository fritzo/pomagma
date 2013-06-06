
include_directories(${CMAKE_SOURCE_DIR}/)


add_library(pomagma_surveyor SHARED main.cpp)
set(POMAGMA_SURVEYOR_LIBS
	pomagma_surveyor
	pomagma_microstructure
	pomagma_platform_concurrent
	pomagma_language
	${POMAGMA_CONCURRENT_LIBS})


set(SRC_DIR ${PROJECT_SOURCE_DIR}/src)

add_custom_command(
	OUTPUT ${CMAKE_CURRENT_LIST_DIR}/h4.theory.cpp
		${SRC_DIR}/theory/h4.compiled
	COMMAND python ${SRC_DIR}/compiler/run.py compile
		${SRC_DIR}/theory/group.rules
		${SRC_DIR}/theory/h4.rules
		${SRC_DIR}/theory/h4.facts
		cpp_out=${CMAKE_CURRENT_LIST_DIR}/h4.theory.cpp
		theory_out=${SRC_DIR}/theory/h4.compiled
		extensional=false
	DEPENDS ${SRC_DIR}/compiler/util.py
		${SRC_DIR}/compiler/expressions.py
		${SRC_DIR}/compiler/sequents.py
		${SRC_DIR}/compiler/parser.py
		${SRC_DIR}/compiler/compiler.py
		${SRC_DIR}/compiler/cpp.py
		${SRC_DIR}/compiler/run.py
		${SRC_DIR}/theory/group.rules
		${SRC_DIR}/theory/h4.rules
		${SRC_DIR}/theory/h4.facts
	)
add_executable(h4.survey h4.theory.cpp)
target_link_libraries(h4.survey ${POMAGMA_SURVEYOR_LIBS})

add_custom_command(
	OUTPUT ${CMAKE_CURRENT_LIST_DIR}/sk.theory.cpp
		${SRC_DIR}/theory/sk.compiled
	COMMAND python ${SRC_DIR}/compiler/run.py compile
		${SRC_DIR}/theory/sk.rules
		${SRC_DIR}/theory/sk.facts
		${SRC_DIR}/theory/order.facts
		cpp_out=${CMAKE_CURRENT_LIST_DIR}/sk.theory.cpp
		theory_out=${SRC_DIR}/theory/sk.compiled
	DEPENDS ${SRC_DIR}/compiler/util.py
		${SRC_DIR}/compiler/expressions.py
		${SRC_DIR}/compiler/sequents.py
		${SRC_DIR}/compiler/parser.py
		${SRC_DIR}/compiler/extensional.py
		${SRC_DIR}/compiler/compiler.py
		${SRC_DIR}/compiler/cpp.py
		${SRC_DIR}/compiler/run.py
		${SRC_DIR}/theory/sk.rules
		${SRC_DIR}/theory/sk.facts
		${SRC_DIR}/theory/order.facts
	)
add_executable(sk.survey sk.theory.cpp)
target_link_libraries(sk.survey ${POMAGMA_SURVEYOR_LIBS})

# TODO get types.rules to compile
add_custom_command(
	OUTPUT ${CMAKE_CURRENT_LIST_DIR}/skj.theory.cpp
		${SRC_DIR}/theory/skj.compiled
	COMMAND python ${SRC_DIR}/compiler/run.py compile
		${SRC_DIR}/theory/sk.rules
		${SRC_DIR}/theory/join.rules
		#${SRC_DIR}/theory/types.rules
		${SRC_DIR}/theory/sk.facts
		${SRC_DIR}/theory/order.facts
		${SRC_DIR}/theory/types.facts
		cpp_out=${CMAKE_CURRENT_LIST_DIR}/skj.theory.cpp
		theory_out=${SRC_DIR}/theory/skj.compiled
	DEPENDS ${SRC_DIR}/compiler/util.py
		${SRC_DIR}/compiler/expressions.py
		${SRC_DIR}/compiler/sequents.py
		${SRC_DIR}/compiler/parser.py
		${SRC_DIR}/compiler/extensional.py
		${SRC_DIR}/compiler/compiler.py
		${SRC_DIR}/compiler/cpp.py
		${SRC_DIR}/compiler/run.py
		${SRC_DIR}/theory/sk.rules
		${SRC_DIR}/theory/join.rules
		${SRC_DIR}/theory/types.rules
		${SRC_DIR}/theory/sk.facts
		${SRC_DIR}/theory/order.facts
		${SRC_DIR}/theory/types.facts
	)
add_executable(skj.survey skj.theory.cpp)
target_link_libraries(skj.survey ${POMAGMA_SURVEYOR_LIBS})

# TODO get reflect.rules to compile
add_custom_command(
	OUTPUT ${CMAKE_CURRENT_LIST_DIR}/skjo.theory.cpp
		${SRC_DIR}/theory/skjo.compiled
	COMMAND python ${SRC_DIR}/compiler/run.py compile
		${SRC_DIR}/theory/sk.rules
		${SRC_DIR}/theory/join.rules
		#${SRC_DIR}/theory/types.rules
		${SRC_DIR}/theory/quote.rules
		#${SRC_DIR}/theory/reflect.rules
		${SRC_DIR}/theory/sk.facts
		${SRC_DIR}/theory/order.facts
		${SRC_DIR}/theory/types.facts
		${SRC_DIR}/theory/quote.facts
		${SRC_DIR}/theory/reflect.facts
		cpp_out=${CMAKE_CURRENT_LIST_DIR}/skjo.theory.cpp
		theory_out=${SRC_DIR}/theory/skjo.compiled
	DEPENDS ${SRC_DIR}/compiler/util.py
		${SRC_DIR}/compiler/expressions.py
		${SRC_DIR}/compiler/sequents.py
		${SRC_DIR}/compiler/parser.py
		${SRC_DIR}/compiler/extensional.py
		${SRC_DIR}/compiler/compiler.py
		${SRC_DIR}/compiler/cpp.py
		${SRC_DIR}/compiler/run.py
		${SRC_DIR}/theory/sk.rules
		${SRC_DIR}/theory/join.rules
		${SRC_DIR}/theory/types.rules
		${SRC_DIR}/theory/quote.rules
		${SRC_DIR}/theory/reflect.rules
		${SRC_DIR}/theory/sk.facts
		${SRC_DIR}/theory/order.facts
		${SRC_DIR}/theory/types.facts
		${SRC_DIR}/theory/quote.facts
		${SRC_DIR}/theory/reflect.facts
	)
add_executable(skjo.survey skjo.theory.cpp)
target_link_libraries(skjo.survey ${POMAGMA_SURVEYOR_LIBS})

