cmake_minimum_required(VERSION 3.5)

project(SlicerElastix)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "https://github.com/lassoan/SlicerElastix")
set(EXTENSION_CATEGORY "Registration")
set(EXTENSION_CONTRIBUTORS "Andras Lasso (PerkLab, Queen's University)")
set(EXTENSION_DESCRIPTION "This extension makes available Elastix medical image registration toolbox (https://elastix.dev) available in Slicer.")
set(EXTENSION_ICONURL "https://raw.githubusercontent.com/lassoan/SlicerElastix/master/SlicerElastix.png")
set(EXTENSION_SCREENSHOTURLS "https://raw.githubusercontent.com/lassoan/SlicerElastix/master/Screenshot01.jpg")
set(EXTENSION_DEPENDS "NA") # Specified as a space separated string, a list or 'NA' if any
set(EXTENSION_BUILD_SUBDIRECTORY inner-build)

set(SUPERBUILD_TOPLEVEL_PROJECT inner)

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})
mark_as_superbuild(Slicer_DIR)

find_package(Git REQUIRED)
mark_as_superbuild(GIT_EXECUTABLE)

#-----------------------------------------------------------------------------
# SuperBuild setup
option(${EXTENSION_NAME}_SUPERBUILD "Build ${EXTENSION_NAME} and the projects it depends on." ON)
mark_as_advanced(${EXTENSION_NAME}_SUPERBUILD)

# The elastix and transformix programs, built from source and run by the module. A build that
# cannot run programs - the WebAssembly build of SlicerWeb, where the module registers with the
# elastix of ITK-Wasm instead (see Elastix/ElastixLib/web_launcher.py) - builds the module alone.
if(EMSCRIPTEN)
  set(_build_elastix_default OFF)
else()
  set(_build_elastix_default ON)
endif()
option(${EXTENSION_NAME}_BUILD_ELASTIX "Build the elastix programs that the module runs." ${_build_elastix_default})
mark_as_advanced(${EXTENSION_NAME}_BUILD_ELASTIX)
mark_as_superbuild(${EXTENSION_NAME}_BUILD_ELASTIX)
if(${EXTENSION_NAME}_SUPERBUILD)
  include("${CMAKE_CURRENT_SOURCE_DIR}/SuperBuild.cmake")
  return()
endif()

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(Elastix)
## NEXT_MODULE

#-----------------------------------------------------------------------------
# Install directory, install project name, install component, and install subdirectory.
set(EXTENSION_CPACK_INSTALL_CMAKE_PROJECTS)
if(${EXTENSION_NAME}_BUILD_ELASTIX)
  list(APPEND EXTENSION_CPACK_INSTALL_CMAKE_PROJECTS "${elastix_DIR};elastix;Executables;/")
endif()
set(${EXTENSION_NAME}_CPACK_INSTALL_CMAKE_PROJECTS "${EXTENSION_CPACK_INSTALL_CMAKE_PROJECTS}" CACHE STRING "List of external projects to install" FORCE)

#-----------------------------------------------------------------------------
list(APPEND CPACK_INSTALL_CMAKE_PROJECTS "${CMAKE_BINARY_DIR};${EXTENSION_NAME};ALL;/")
list(APPEND CPACK_INSTALL_CMAKE_PROJECTS "${${EXTENSION_NAME}_CPACK_INSTALL_CMAKE_PROJECTS}")
include(${Slicer_EXTENSION_GENERATE_CONFIG})
include(${Slicer_EXTENSION_CPACK})
