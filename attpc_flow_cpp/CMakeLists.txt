# Require the cmake minimum version.
cmake_minimum_required(VERSION 3.10)

if (NOT SKBUILD)
  message(WARNING "\
  This CMake file is meant to be executed using 'scikit-build'. Running
  it directly will almost certainly not produce the desired result. If
  you are a user trying to install this package, please use the command
  below, which will install all necessary build dependencies, compile
  the package in an isolated environment, and then install it.
  =====================================================================
   $ pip install .
  =====================================================================
  If you are a software developer, and this is your own package, then
  it is usually much more efficient to install the build dependencies
  in your environment once and use the following command that avoids
  a costly creation of a new virtual environment at every compilation:
  =====================================================================
   $ pip install nanobind scikit-build-core[pyproject]
   $ pip install --no-build-isolation -ve .
  =====================================================================
  You may optionally add -Ceditable.rebuild=true to auto-rebuild when
  the package is imported. Otherwise, you need to re-run the above
  after editing C++ files.")
endif()

# Set project properties.
project(
	${SKBUILD_PROJECT_NAME}
	VERSION ${SKBUILD_PROJECT_VERSION}
	DESCRIPTION "Nodes extensions written in C++ for ATTPC-flow."
	LANGUAGES CXX
)

cmake_policy(SET CMP0135 NEW)

# Require out-of-source builds
file(TO_CMAKE_PATH "${PROJECT_BINARY_DIR}/CMakeLists.txt" LOC_PATH)
if (EXISTS "${LOC_PATH}")
	message(FATAL_ERROR "You cannot build in a source directory (or any directory with"
						"CmakeLists.txt file). Please make a build subdirectory. Feel free"
						"to remove CMakeCache.txt and CMakeFiles.")
endif()

# Set the build type
if(NOT CMAKE_BUILD_TYPE)
	set(CMAKE_BUILD_TYPE Release)
endif()


# Only do these if this is the main project, and not if it is included
# through add_subdirectory
if (CMAKE_PROJECT_NAME STREQUAL PROJECT_NAME)

	# Let's ensure -std=c++xx instead of -std=g++xx
	set(CMAKE_CXX_EXTENSIONS OFF)

	# Set the default cxx standard
	set(CMAKE_CXX_STANDARD 17)
	set(CMAKE_CXX_STANDARD_REQUIRED ON)

	# Set default compile options
	set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Werror -Wall -Wextra")

	# Let's nicely support folders in IDE's
	set_property(GLOBAL PROPERTY USE_FOLDERS ON)
endif()

# Try to import all Python components potentially needed by nanobind
# find python
if (CMAKE_VERSION VERSION_LESS 3.18)
  set(DEV_MODULE Development)
else()
  set(DEV_MODULE Development.Module)
endif()
find_package(Python 3.9
  REQUIRED COMPONENTS Interpreter ${DEV_MODULE}
  OPTIONAL_COMPONENTS Development.SABIModule)

# Import nanobind through CMake's find_package mechanism
find_package(nanobind CONFIG REQUIRED)

# Option to enable ZeroMQ support (default ON for extensions.)
set(ATTPC_FLOW_USE_ZMQ ON CACHE BOOL "Enable ZeroMQ support for progress reporting")
# Only set default if not already defined (e.g., by parent CMakeLists.txt)
if(NOT DEFINED ATTPC_FLOW_USE_ZMQ)
	option(ATTPC_FLOW_USE_ZMQ "Enable ZeroMQ support for progress reporting" OFF)
endif()


# find ZeroMQ only if option is enabled
if(ATTPC_FLOW_USE_ZMQ)
	find_package(ZeroMQ QUIET)
	# libzmq autotools install: fallback to pkg-config
	if(NOT ZeroMQ_FOUND)
		message(STATUS "CMake libzmq package not found, trying again with pkg-config (normal install of zeromq)")
		list(APPEND CMAKE_MODULE_PATH ${CMAKE_CURRENT_LIST_DIR} "${CMAKE_CURRENT_LIST_DIR}/cmake")
		find_package(ZeroMQ REQUIRED)
	endif()
	# Add compile definition
	add_compile_definitions(ATTPC_FLOW_USE_ZMQ)
	message(STATUS "ZeroMQ support: ENABLED")
else()
	message(STATUS "ZeroMQ support: DISABLED")
endif()

# Option to enable tests (default OFF for development)
option(BUILD_TESTS "Build unit tests" OFF)
option(BUILD_BIN "Build executable binary" OFF)

function(show_config_options)
	message("")
	message("Build Properties")
	message("  c++ compiler.................: " ${CMAKE_CXX_COMPILER})
	message("  c++ stardard.................: " ${CMAKE_CXX_STANDARD})
	message("  python interpreter...........: " ${Python_INTERPRETER_ID})
	message("  python version...............: " ${Python_VERSION})
	message("  python include dirs..........: " ${Python_INCLUDE_DIRS})
	message("  cmake........................: " ${CMAKE_VERSION})
	message("  cmake build type.............: " ${CMAKE_BUILD_TYPE})
	message("Build Options")
	message("  ZeroMQ support...............: " ${ATTPC_FLOW_USE_ZMQ})
	message("  Build tests..................: " ${BUILD_TESTS})
	message("  Build binary.................: " ${BUILD_BIN})
	message("")
endfunction()

show_config_options()

add_subdirectory(src)
add_subdirectory(extensions)
if (BUILD_BIN)
	add_subdirectory(bin)
endif()
if(BUILD_TESTS)
	enable_testing()
	add_subdirectory(tests)
endif()