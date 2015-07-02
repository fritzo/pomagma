include_directories(${CMAKE_SOURCE_DIR}/include)

add_library(pomagma_surveyor SHARED theory.cpp)

add_executable(init init_main.cpp)
target_link_libraries(init
	pomagma_surveyor
	${POMAGMA_CHART_LIBS}
)

add_executable(survey survey_main.cpp)
target_link_libraries(survey
	pomagma_surveyor
	${POMAGMA_CHART_LIBS}
)
