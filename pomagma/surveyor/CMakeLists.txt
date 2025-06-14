include_directories(${CMAKE_SOURCE_DIR})

add_library(pomagma_surveyor SHARED theory.cpp)
target_link_libraries(pomagma_surveyor
	${POMAGMA_CHART_LIBS}
)

pomagma_add_executable(init init_main.cpp)
target_link_libraries(init
	pomagma_surveyor
	${POMAGMA_CHART_LIBS}
)

pomagma_add_executable(survey survey_main.cpp)
target_link_libraries(survey
	pomagma_surveyor
	${POMAGMA_CHART_LIBS}
)
