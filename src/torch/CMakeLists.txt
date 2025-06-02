# Include the main include directory
include_directories(${CMAKE_SOURCE_DIR}/include)

# Collect source files
set(TORCH_EXTENSION_SOURCES
    structure.cpp
    extension.cpp
)

# Create shared library for the torch extension
add_library(pomagma_torch SHARED ${TORCH_EXTENSION_SOURCES})

# Set target properties for PyTorch extension
set_target_properties(pomagma_torch PROPERTIES
    CXX_STANDARD 17
    CXX_STANDARD_REQUIRED ON
    PREFIX ""  # Remove lib prefix to get pomagma_torch.so instead of libpomagma_torch.so
    SUFFIX ".so"  # Ensure .so extension
    POSITION_INDEPENDENT_CODE ON
)

# Link against PyTorch libraries and Pomagma libraries
target_link_libraries(pomagma_torch PRIVATE 
    ${TORCH_LIBRARIES}
    pomagma_atlas
    ${POMAGMA_IO_LIBS}
    ${POMAGMA_UTIL_LIBS}
)

# Include directories
target_include_directories(pomagma_torch PRIVATE
    ${TORCH_INCLUDE_DIRS}
    ${CMAKE_SOURCE_DIR}/include
)

# Set compiler flags
target_compile_options(pomagma_torch PRIVATE 
    ${TORCH_CXX_FLAGS}
)

# Ensure proper compilation definitions for PyTorch
target_compile_definitions(pomagma_torch PRIVATE
    -DTORCH_EXTENSION_NAME=pomagma_torch
)

# Install the shared library to a standard location
install(TARGETS pomagma_torch
    LIBRARY DESTINATION lib
    RUNTIME DESTINATION bin
    ARCHIVE DESTINATION lib
) 