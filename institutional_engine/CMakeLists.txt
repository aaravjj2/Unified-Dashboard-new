# ==============================================================================
# CMakeLists.txt - Institutional Engine Build Configuration
# ==============================================================================
#
# High-Performance Limit Order Book (LOB) Matching Engine
# 
# Build Instructions:
#   mkdir build && cd build
#   cmake .. -DCMAKE_BUILD_TYPE=Release
#   make -j$(nproc)
#
# Requirements:
#   - CMake 3.14+
#   - C++20 compliant compiler (GCC 10+, Clang 10+)
#   - Python 3.8+ with pybind11
#
# ==============================================================================

cmake_minimum_required(VERSION 3.14)

# Project definition
project(institutional_engine
    VERSION 1.0.0
    DESCRIPTION "High-Performance C++20 Limit Order Book for Quantitative Trading"
    LANGUAGES CXX
)

# ==============================================================================
# BUILD OPTIONS
# ==============================================================================

option(BUILD_TESTS "Build test suite" ON)
option(ENABLE_LTO "Enable Link-Time Optimization" ON)
option(NATIVE_ARCH "Optimize for native CPU architecture" ON)

# ==============================================================================
# C++ STANDARD & COMPILER FLAGS
# ==============================================================================

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Position Independent Code (required for shared libraries)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

# Compiler-specific flags
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    # Optimization flags for Release builds
    set(CMAKE_CXX_FLAGS_RELEASE "-O3 -DNDEBUG")
    
    # Native architecture optimization (AVX2/AVX-512 if available)
    if(NATIVE_ARCH)
        set(CMAKE_CXX_FLAGS_RELEASE "${CMAKE_CXX_FLAGS_RELEASE} -march=native")
    endif()
    
    # Link-Time Optimization
    if(ENABLE_LTO)
        set(CMAKE_CXX_FLAGS_RELEASE "${CMAKE_CXX_FLAGS_RELEASE} -flto")
        set(CMAKE_EXE_LINKER_FLAGS_RELEASE "${CMAKE_EXE_LINKER_FLAGS_RELEASE} -flto")
    endif()
    
    # Warning flags
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -Wextra -Wpedantic")
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wno-unused-parameter")
    
    # Debug flags
    set(CMAKE_CXX_FLAGS_DEBUG "-g -O0 -DDEBUG")
endif()

# ==============================================================================
# FIND DEPENDENCIES
# ==============================================================================

# Find Python and pybind11
find_package(Python3 REQUIRED COMPONENTS Interpreter Development)

# Try to find pybind11 via CMake config
find_package(pybind11 CONFIG QUIET)

if(NOT pybind11_FOUND)
    # Fallback: fetch pybind11 from GitHub
    message(STATUS "pybind11 not found, fetching from GitHub...")
    
    include(FetchContent)
    FetchContent_Declare(
        pybind11
        GIT_REPOSITORY https://github.com/pybind/pybind11.git
        GIT_TAG v2.11.1
    )
    FetchContent_MakeAvailable(pybind11)
endif()

# ==============================================================================
# SOURCE FILES
# ==============================================================================

set(LOB_SOURCES
    ${CMAKE_CURRENT_SOURCE_DIR}/src/OrderBook.cpp
)

set(LOB_HEADERS
    ${CMAKE_CURRENT_SOURCE_DIR}/src/Order.h
    ${CMAKE_CURRENT_SOURCE_DIR}/src/OrderBook.h
)

# ==============================================================================
# BUILD TARGETS
# ==============================================================================

# Create the Python extension module
pybind11_add_module(institutional_engine
    ${LOB_SOURCES}
    ${CMAKE_CURRENT_SOURCE_DIR}/src/PyBindWrapper.cpp
)

# Include directories
target_include_directories(institutional_engine PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/src
)

# Set output name and properties
set_target_properties(institutional_engine PROPERTIES
    OUTPUT_NAME "institutional_engine"
    LIBRARY_OUTPUT_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
)

# ==============================================================================
# INSTALLATION (Optional)
# ==============================================================================

# Install the Python module to site-packages
install(TARGETS institutional_engine
    LIBRARY DESTINATION ${Python3_SITEARCH}
)

# ==============================================================================
# STATUS OUTPUT
# ==============================================================================

message(STATUS "")
message(STATUS "=== Institutional Engine Build Configuration ===")
message(STATUS "Version:          ${PROJECT_VERSION}")
message(STATUS "C++ Standard:     ${CMAKE_CXX_STANDARD}")
message(STATUS "Build Type:       ${CMAKE_BUILD_TYPE}")
message(STATUS "Compiler:         ${CMAKE_CXX_COMPILER_ID} ${CMAKE_CXX_COMPILER_VERSION}")
message(STATUS "Python:           ${Python3_VERSION}")
message(STATUS "pybind11:         ${pybind11_VERSION}")
message(STATUS "Native Arch:      ${NATIVE_ARCH}")
message(STATUS "LTO Enabled:      ${ENABLE_LTO}")
message(STATUS "")





