set(proj elastix)
set(ep_common_cxx_flags "${CMAKE_CXX_FLAGS_INIT} ${ADDITIONAL_CXX_FLAGS}")
# Set dependency list
set(${proj}_DEPENDS "")

# Include dependent projects if any
ExternalProject_Include_Dependencies(${proj} PROJECT_VAR proj)

if(${CMAKE_PROJECT_NAME}_USE_SYSTEM_${proj})
  message(FATAL_ERROR "Enabling ${CMAKE_PROJECT_NAME}_USE_SYSTEM_${proj} is not supported !")
endif()

# Sanity checks
if(DEFINED elastix_DIR AND NOT EXISTS ${elastix_DIR})
  message(FATAL_ERROR "elastix_DIR variable is defined but corresponds to nonexistent directory")
endif()

if(NOT DEFINED ${proj}_DIR AND NOT ${CMAKE_PROJECT_NAME}_USE_SYSTEM_${proj})

  if(NOT DEFINED git_protocol)
    set(git_protocol "git")
  endif()

  set(${proj}_INSTALL_DIR ${CMAKE_BINARY_DIR}/${proj}-install)
  set(${proj}_DIR ${CMAKE_BINARY_DIR}/${proj}-build)

  if (APPLE)
    set(${proj}_cxx_flags "${ep_common_cxx_flags} -Wno-inconsistent-missing-override")
  endif()

  message(STATUS "ITK version: ${ITK_VERSION_MAJOR}.${ITK_VERSION_MINOR}.${ITK_VERSION_PATCH}.")
  if(${ITK_VERSION_MAJOR}.${ITK_VERSION_MINOR} VERSION_LESS 5.0)
    set(ELASTIX_GIT_REPOSITORY "${git_protocol}://github.com/SuperElastix/elastix.git")
    set(ELASTIX_GIT_TAG "419313e9cc12727d73c7e6e47fbdf960aa1218b9") # latest commit on "develop" branch as if 2019-10-13
  else()
    set(ELASTIX_GIT_REPOSITORY "${git_protocol}://github.com/lassoan/elastix.git")
    # This branch contains SuperElastix/elastix "develop" branch as of 2020-04-12
    # with fix for build error caused by recent ITK5 changes.
    set(ELASTIX_GIT_TAG "ITK-v5.1rc03")
  endif()

  ExternalProject_Add(${proj}
    # Slicer
    ${${proj}_EP_ARGS}
    SOURCE_DIR ${CMAKE_BINARY_DIR}/${proj}
    #SOURCE_SUBDIR src # requires CMake 3.7 or later
    BINARY_DIR ${proj}-build
    INSTALL_DIR ${${proj}_INSTALL_DIR}
    GIT_REPOSITORY ${ELASTIX_GIT_REPOSITORY}
    GIT_TAG ${ELASTIX_GIT_TAG}
    #--Patch step-------------
    PATCH_COMMAND ${CMAKE_COMMAND} -Delastix_SRC_DIR=${CMAKE_BINARY_DIR}/${proj}
      -P ${CMAKE_CURRENT_LIST_DIR}/${proj}_patch.cmake
    #--Configure step-------------
    CMAKE_CACHE_ARGS
      -DSubversion_SVN_EXECUTABLE:STRING=${Subversion_SVN_EXECUTABLE}
      -DGIT_EXECUTABLE:STRING=${GIT_EXECUTABLE}
      -DITK_DIR:STRING=${ITK_DIR}
      -DUSE_KNNGraphAlphaMutualInformationMetric:BOOL=OFF
      -DCMAKE_CXX_COMPILER:FILEPATH=${CMAKE_CXX_COMPILER}
      -DCMAKE_CXX_FLAGS:STRING=${${proj}_cxx_flags}
      -DCMAKE_C_COMPILER:FILEPATH=${CMAKE_C_COMPILER}
      -DCMAKE_C_FLAGS:STRING=${ep_common_c_flags}
      -DCMAKE_CXX_STANDARD:STRING=${CMAKE_CXX_STANDARD}
      -DCMAKE_BUILD_TYPE:STRING=${CMAKE_BUILD_TYPE}
      -DBUILD_TESTING:BOOL=OFF
      -DCMAKE_MACOSX_RPATH:BOOL=0
      # location of elastix.exe and transformix.exe in the build tree:
      -DCMAKE_RUNTIME_OUTPUT_DIRECTORY:PATH=${CMAKE_BINARY_DIR}/${Slicer_THIRDPARTY_BIN_DIR}
      -DCMAKE_LIBRARY_OUTPUT_DIRECTORY:PATH=${CMAKE_BINARY_DIR}/${Slicer_THIRDPARTY_LIB_DIR}
      -DCMAKE_ARCHIVE_OUTPUT_DIRECTORY:PATH=${CMAKE_ARCHIVE_OUTPUT_DIRECTORY}
      -DELASTIX_RUNTIME_DIR:STRING=${Slicer_INSTALL_THIRDPARTY_LIB_DIR}
      -DELASTIX_LIBRARY_DIR:STRING=${Slicer_INSTALL_THIRDPARTY_LIB_DIR}
    #--Build step-----------------
    #--Install step-----------------
    # Don't perform installation at the end of the build
    INSTALL_COMMAND ""
    DEPENDS
      ${${proj}_DEPENDS}
    )
  #set(${proj}_DIR ${${proj}_INSTALL_DIR})
  #if(UNIX)
  #  set(${proj}_DIR ${${proj}_INSTALL_DIR}/share/elastix)
  #endif()

else()
  ExternalProject_Add_Empty(${proj} DEPENDS ${${proj}_DEPENDS})
endif()

mark_as_superbuild(${proj}_DIR:PATH)
