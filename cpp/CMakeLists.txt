# Require the cmake minimum version.
cmake_minimum_required(VERSION 3.10)


# Set project properties.
project(
	ATTPC_FLOW_CPP
	VERSION 0.1.0
	DESCRIPTION "ATTPC flow analysis framework."
	LANGUAGES CXX
)

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

	# Set default compile options
	set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Werror -Wall -Wextra")

	# Let's nicely support folders in IDE's
	set_property(GLOBAL PROPERTY USE_FOLDERS ON)
endif()

# Option to enable ZeroMQ support (default OFF for standalone cpp build)
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


function(show_config_options)
	message("")
	message("Build Properties")
	message("  c++ compiler.................: " ${CMAKE_CXX_COMPILER})
	message("  c++ stardard.................: " ${CMAKE_CXX_STANDARD})
	message("  cmake........................: " ${CMAKE_VERSION})
	message("  cmake build type.............: " ${CMAKE_BUILD_TYPE})
	message("")
endfunction()

show_config_options()

add_subdirectory(src)
add_subdirectory(bin)