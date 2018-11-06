# Elastix does not define install components. We don't want to include
# .lib and .h files in the extension package, therefore we modify CMakeLists.txt
# files to specify RuntimeLibraries component for the files that we want to include
# in the extension package.

set(runtime_libraries_cmakelists
  ${elastix_SRC_DIR}/Components/Metrics/KNNGraphAlphaMutualInformation/KNN/CMakeLists.txt
  ${elastix_SRC_DIR}/Components/Metrics/KNNGraphAlphaMutualInformation/KNN/ann_1.1/CMakeLists.txt
  ${elastix_SRC_DIR}/Core/CMakeLists.txt)

foreach(cmakefile ${runtime_libraries_cmakelists})
  file(READ ${cmakefile} cmakefile_src)
  string(FIND "${cmakefile_src}" "COMPONENT RuntimeLibraries" found_patched)
  if ("${found_patched}" LESS 0)
    message(STATUS "elastix: Patching ${cmakefile}")
    string(REPLACE "RUNTIME DESTINATION \${ELASTIX_RUNTIME_DIR} )" "RUNTIME DESTINATION \${ELASTIX_RUNTIME_DIR}
      COMPONENT RuntimeLibraries )"
      cmakefile_src "${cmakefile_src}")
    file(WRITE ${cmakefile} "${cmakefile_src}")
  else()
    message(STATUS "elastix: Already patched ${cmakefile}")
  endif()
endforeach()

# Make directory name shorter to allow Windows builds
if (WIN32)
  if (EXISTS ${elastix_SRC_DIR}/src/Components/ResampleInterpolators/ReducedDimensionBSplineResampleInterpolator)
    message(STATUS "elastix: Patching ReducedDimensionBSplineResampleInterpolator")
    file(RENAME
      ${elastix_SRC_DIR}/src/Components/ResampleInterpolators/ReducedDimensionBSplineResampleInterpolator
      ${elastix_SRC_DIR}/src/Components/ResampleInterpolators/RDBSplineResampleInterpolator)
  else()
    message(STATUS "elastix: Already patched ReducedDimensionBSplineResampleInterpolator")
  endif()
endif (WIN32)
