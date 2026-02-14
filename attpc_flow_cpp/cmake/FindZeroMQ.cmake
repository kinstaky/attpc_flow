# FindZeroMQ.cmake
# Locates the ZeroMQ (libzmq) C library and headers

find_package(PkgConfig QUIET)
if(PKG_CONFIG_FOUND)
    pkg_check_modules(PC_LIBZMQ QUIET libzmq)
endif()

# Find the C header (zmq.h) - Required for the C++ header to function
find_path(ZeroMQ_INCLUDE_DIR
    NAMES zmq.h
    PATHS ${PC_LIBZMQ_INCLUDE_DIRS} /usr/include /usr/local/include
)

# Find the binary library (libzmq.so)
find_library(ZeroMQ_LIBRARY
    NAMES zmq
    PATHS ${PC_LIBZMQ_LIBRARY_DIRS} /usr/lib /usr/local/lib /usr/lib/x86_64-linux-gnu
)

set(ZeroMQ_VERSION ${PC_LIBZMQ_VERSION})

# Handle the REQUIRED/QUIET arguments and set ZeroMQ_FOUND
include(FindPackageHandleStandardArgs)
find_package_handle_standard_args(ZeroMQ
    FOUND_VAR ZeroMQ_FOUND
    REQUIRED_VARS ZeroMQ_LIBRARY ZeroMQ_INCLUDE_DIR
    VERSION_VAR ZeroMQ_VERSION
)

# Create the imported target
if(ZeroMQ_FOUND AND NOT TARGET ZeroMQ::ZeroMQ)
    add_library(ZeroMQ::ZeroMQ UNKNOWN IMPORTED)
    set_target_properties(ZeroMQ::ZeroMQ PROPERTIES
        IMPORTED_LOCATION "${ZeroMQ_LIBRARY}"
        INTERFACE_INCLUDE_DIRECTORIES "${ZeroMQ_INCLUDE_DIR}"
    )
endif()

mark_as_advanced(ZeroMQ_INCLUDE_DIR ZeroMQ_LIBRARY)