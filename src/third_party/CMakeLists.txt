include_directories(${CMAKE_SOURCE_DIR}/include)

# Google test assumes undefined macros default to 0.
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wno-error=undef -Wno-undef")

add_subdirectory(farmhash)
add_subdirectory(googlemock)
# add_subdirectory(googletest)  # Added by googlemock.
