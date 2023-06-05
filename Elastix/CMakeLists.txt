#-----------------------------------------------------------------------------
set(MODULE_NAME Elastix)

#-----------------------------------------------------------------------------
set(MODULE_PYTHON_SCRIPTS
  ${MODULE_NAME}.py
  )

set(MODULE_PYTHON_RESOURCES
  Resources/Icons/${MODULE_NAME}.png
  Resources/UI/${MODULE_NAME}.ui
  )
  
set(REGISTRATION_PARAMETER_FILES
  ElastixParameterSetDatabase.xml
  Bsplines_parameter-file.txt
  Deformable.txt
  Par0000affine.txt
  Par0000bspline.txt
  Par0001affine.txt
  Par0001bspline04.txt
  Par0001bspline08.txt
  Par0001bspline16.txt
  Par0001bspline32.txt
  Par0001bspline64.txt
  Par0001rigid.txt
  Par0001translation.txt
  Par0002.fs.MI.rigid.Full.txt
  Par0002.fs.MI.rigid.Random.txt
  Par0002.fs.MI.rigid.RandomCoordinate.txt
  Par0003.affine.txt
  Par0003.bs-R1-fg.txt
  Par0003.bs-R1-ug.txt
  Par0003.bs-R2-fg.txt
  Par0003.bs-R2-ug.txt
  Par0003.bs-R3-fg.txt
  Par0003.bs-R3-ug.txt
  Par0003.bs-R4-fg.txt
  Par0003.bs-R4-ug.txt
  Par0003.bs-R5-fg.txt
  Par0003.bs-R5-ug.txt
  Par0003.bs-R6-fg.txt
  Par0003.bs-R6-ug.txt
  Par0003.bs-R7-fg.txt
  Par0003.bs-R7-ug.txt
  Par0003.bs-R8-fg.txt
  Par0003.bs-R8-ug.txt
  Par0010affine.txt
  Par0010bspline.txt
  Par0013Powell_NGC_singleImage.txt
  Par0017_cartilage_RigidLMI.txt
  Par0018_2D_rigid_MI.txt
  Par0018_2D_translation_MI.txt
  Par0018_3D_affine_MI.txt
  Par0018_3D_bspline_MI_15.txt
  Par0018_3D_rigid_MI.txt
  Par0020affine.txt
  Par0020bspline1.txt
  Par0020bspline2.txt
  Par0020bspline3.txt
  Par0020rigid.txt
  Par0025affine.txt
  Par0025bspline.txt
  Par0025rigid.txt
  Par0026affine.txt
  Par0026bspline.txt
  Par0026rigid.txt
  Par0032_bsplines.txt
  Par0032_rigid.txt
  Par0033bspline.txt
  Par0033rigid.txt
  Par0033similarity.txt
  Par0034affine.txt
  Par0034bspline.txt
  Par0034rigid.txt
  Par0040affine.txt
  Par0041bspline.txt
  Par0041similarity.txt
  Par0042bspline.txt
  Par0042rigid.txt
  Par0043rigid.txt
  Par0044Affine.txt
  Par0044NonRigid.txt
  Parameters.MI.Coarse.Bspline_tuned.txt
  Parameters.MI.Fine.Bspline_tuned.txt
  Parameters.MI.RP.Bspline_tuned.txt
  Parameters.NCC.txt
  Parameters.NCC_EDM.txt
  Parameters.Par0008.affine.txt
  Parameters.Par0008.elastic.txt
  Parameters.Par0009.affine.txt
  Parameters.Par0009.elastic.txt
  Parameters.Par0011.affine.txt
  Parameters.Par0011.bspline1.txt
  Parameters.Par0011.bspline1_s.txt
  Parameters.Par0011.bspline2.txt
  Parameters.Par0011.bspline2_s.txt
  Parameters.Par0015.expA.patient.LNC.bspline.txt
  Parameters.Par0015.expA.patient.NC.affine.txt
  Parameters.Par0015.expA.patient.NC.bspline.txt
  Parameters.Par0015.expB.phantom.NC_EDM.affine.txt
  Parameters.Par0015.expB.phantom.NC_EDM.bspline.txt
  Parameters.Par0015.expC.phantom.NC.affine.txt
  Parameters.Par0015.expC.phantom.NC.bspline.txt
  Parameters.Par0015.expD.phantom.NC.rigid.txt
  Parameters.similarity.txt
  Parameters0030_Affine.txt
  Parameters0030_Bspline.txt
  Parameters0030_Euler.txt
  Parameters_Affine.txt
  Parameters_BSpline.txt
  Parameters_BSplineNCC.txt
  Parameters_Rigid.txt
  Parameters_RigidAMS.txt
  Parameters_Translation.txt
  Rigid.txt
  Rigid_parameter-file.txt
  )

foreach (paramfile ${REGISTRATION_PARAMETER_FILES})
  set(MODULE_PYTHON_RESOURCES ${MODULE_PYTHON_RESOURCES} "Resources/RegistrationParameters/${paramfile}")
endforeach()

#-----------------------------------------------------------------------------
slicerMacroBuildScriptedModule(
  NAME ${MODULE_NAME}
  SCRIPTS ${MODULE_PYTHON_SCRIPTS}
  RESOURCES ${MODULE_PYTHON_RESOURCES}
  WITH_GENERIC_TESTS
  )

#-----------------------------------------------------------------------------
if(BUILD_TESTING)
  # Register the unittest subclass in the main script as a ctest.
  # Note that the test will also be available at runtime.
  slicer_add_python_unittest(SCRIPT ${MODULE_NAME}.py)

  # Additional build-time testing
  add_subdirectory(Testing)
endif()
