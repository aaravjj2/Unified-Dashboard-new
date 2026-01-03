#!/bin/bash
# ==============================================================================
# build_and_test.sh - Build and Test Institutional Engine
# ==============================================================================
#
# Usage:
#   chmod +x tests/build_and_test.sh
#   ./tests/build_and_test.sh
#
# ==============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

echo ""
echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}🏛️  INSTITUTIONAL ENGINE - BUILD & TEST${NC}"
echo -e "${BLUE}============================================================${NC}"
echo ""

# Change to project directory
cd "$PROJECT_DIR"
echo -e "${YELLOW}📁 Working directory: ${PROJECT_DIR}${NC}"

# ==============================================================================
# STEP 1: Check Dependencies
# ==============================================================================

echo ""
echo -e "${YELLOW}📋 STEP 1: Checking dependencies...${NC}"

# Check CMake
if ! command -v cmake &> /dev/null; then
    echo -e "${RED}❌ CMake not found. Please install cmake.${NC}"
    echo "   Ubuntu/Debian: sudo apt install cmake"
    exit 1
fi
echo -e "${GREEN}   ✅ CMake: $(cmake --version | head -n1)${NC}"

# Check C++ compiler
if command -v g++ &> /dev/null; then
    CXX_COMPILER="g++"
    CXX_VERSION=$(g++ --version | head -n1)
elif command -v clang++ &> /dev/null; then
    CXX_COMPILER="clang++"
    CXX_VERSION=$(clang++ --version | head -n1)
else
    echo -e "${RED}❌ No C++ compiler found. Please install g++ or clang++.${NC}"
    echo "   Ubuntu/Debian: sudo apt install g++"
    exit 1
fi
echo -e "${GREEN}   ✅ C++ Compiler: ${CXX_VERSION}${NC}"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 not found. Please install python3.${NC}"
    exit 1
fi
PYTHON_VERSION=$(python3 --version)
echo -e "${GREEN}   ✅ Python: ${PYTHON_VERSION}${NC}"

# Check pybind11
if ! python3 -c "import pybind11" 2>/dev/null; then
    echo -e "${YELLOW}   ⚠️ pybind11 not found. Installing...${NC}"
    pip3 install pybind11 --quiet
fi
PYBIND_VERSION=$(python3 -c "import pybind11; print(pybind11.__version__)" 2>/dev/null || echo "unknown")
echo -e "${GREEN}   ✅ pybind11: ${PYBIND_VERSION}${NC}"

# ==============================================================================
# STEP 2: Create Build Directory
# ==============================================================================

echo ""
echo -e "${YELLOW}📁 STEP 2: Creating build directory...${NC}"

BUILD_DIR="$PROJECT_DIR/build"

if [ -d "$BUILD_DIR" ]; then
    echo "   Cleaning existing build directory..."
    rm -rf "$BUILD_DIR"
fi

mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"
echo -e "${GREEN}   ✅ Build directory: ${BUILD_DIR}${NC}"

# ==============================================================================
# STEP 3: Configure with CMake
# ==============================================================================

echo ""
echo -e "${YELLOW}🔧 STEP 3: Configuring with CMake...${NC}"

# Get pybind11 cmake dir
PYBIND11_CMAKE_DIR=$(python3 -c "import pybind11; print(pybind11.get_cmake_dir())" 2>/dev/null || echo "")

CMAKE_ARGS="-DCMAKE_BUILD_TYPE=Release"

if [ -n "$PYBIND11_CMAKE_DIR" ]; then
    CMAKE_ARGS="$CMAKE_ARGS -Dpybind11_DIR=$PYBIND11_CMAKE_DIR"
fi

echo "   Running: cmake .. $CMAKE_ARGS"
cmake .. $CMAKE_ARGS

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ CMake configuration failed!${NC}"
    exit 1
fi
echo -e "${GREEN}   ✅ CMake configuration complete${NC}"

# ==============================================================================
# STEP 4: Build
# ==============================================================================

echo ""
echo -e "${YELLOW}🔨 STEP 4: Building (this may take a moment)...${NC}"

# Detect number of cores
NPROC=$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)
echo "   Using ${NPROC} parallel jobs"

make -j${NPROC}

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Build failed!${NC}"
    exit 1
fi

# Check for the built module
MODULE_PATH=$(find "$PROJECT_DIR" -name "institutional_engine*.so" -o -name "institutional_engine*.pyd" 2>/dev/null | head -1)

if [ -z "$MODULE_PATH" ]; then
    echo -e "${RED}❌ Built module not found!${NC}"
    exit 1
fi

echo -e "${GREEN}   ✅ Build complete!${NC}"
echo -e "${GREEN}   📦 Module: ${MODULE_PATH}${NC}"

# ==============================================================================
# STEP 5: Run Tests
# ==============================================================================

echo ""
echo -e "${YELLOW}🧪 STEP 5: Running Python test suite...${NC}"
echo ""

cd "$PROJECT_DIR"

# Run the test suite
python3 tests/test_lob_core.py
TEST_RESULT=$?

# ==============================================================================
# STEP 6: Summary
# ==============================================================================

echo ""
echo -e "${BLUE}============================================================${NC}"
if [ $TEST_RESULT -eq 0 ]; then
    echo -e "${GREEN}🎉 BUILD AND TEST SUCCESSFUL!${NC}"
    echo ""
    echo "   The institutional_engine module is ready to use."
    echo ""
    echo "   Usage from Python:"
    echo "     import institutional_engine as ie"
    echo "     book = ie.OrderBook('SPY')"
    echo "     book.add_order(1, 450.0, 100, True)  # Buy 100 @ 450"
    echo ""
else
    echo -e "${RED}⚠️  TESTS FAILED - See output above${NC}"
fi
echo -e "${BLUE}============================================================${NC}"
echo ""

exit $TEST_RESULT





