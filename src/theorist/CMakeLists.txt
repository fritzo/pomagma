include_directories(${CMAKE_SOURCE_DIR}/include)

add_library(pomagma_theorist SHARED
	hypothesize.cpp
	consistency.cpp
	conjecture_equal.cpp
	conjecture_diverge.cpp
)
target_link_libraries(pomagma_theorist
	${POMAGMA_WORLD_LIBS}
)
set(POMAGMA_THEORIST_LIBS
	pomagma_theorist
	${POMAGMA_WORLD_LIBS}
)

add_executable(try_prove_nless try_prove_nless_main.cpp)
target_link_libraries(try_prove_nless ${POMAGMA_THEORIST_LIBS})
