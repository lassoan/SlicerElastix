import os
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging

#
# Elastix
#

class Elastix(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "General Registration (Elastix)"
    self.parent.categories = ["Registration"]
    self.parent.dependencies = []
    self.parent.contributors = ["John Doe (AnyWare Corp.)"] # replace with "Firstname Lastname (Organization)"
    self.parent.helpText = """
This is an example of scripted loadable module bundled in an extension.
It performs a simple thresholding on the input volume and optionally captures a screenshot.
"""
    self.parent.helpText += self.getDefaultModuleDocumentationLink()
    self.parent.acknowledgementText = """
This file was originally developed by Jean-Christophe Fillion-Robin, Kitware Inc.
and Steve Pieper, Isomics, Inc. and was partially funded by NIH grant 3P41RR013218-12S1.
""" # replace with organization, grant and thanks.

#
# ElastixWidget
#

class ElastixWidget(ScriptedLoadableModuleWidget):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)

    self.logic = ElastixLogic()
    self.logic.logCallback = self.addLog
    self.registrationInProgress = False
    
    # Instantiate and connect widgets ...

    # Parameter sets
    defaultinputParametersCollapsibleButton = ctk.ctkCollapsibleButton()
    defaultinputParametersCollapsibleButton.text = "Parameter set"
    defaultinputParametersCollapsibleButton.collapsed = True
    self.layout.addWidget(defaultinputParametersCollapsibleButton)
    defaultParametersLayout = qt.QFormLayout(defaultinputParametersCollapsibleButton)

    self.parameterNodeSelector = slicer.qMRMLNodeComboBox()
    self.parameterNodeSelector.nodeTypes = ["vtkMRMLScriptedModuleNode"]
    self.parameterNodeSelector.addAttribute( "vtkMRMLScriptedModuleNode", "ModuleName", "Elastix" )
    self.parameterNodeSelector.selectNodeUponCreation = True
    self.parameterNodeSelector.addEnabled = True
    self.parameterNodeSelector.renameEnabled = True
    self.parameterNodeSelector.removeEnabled = True
    self.parameterNodeSelector.noneEnabled = False
    self.parameterNodeSelector.showHidden = True
    self.parameterNodeSelector.showChildNodeTypes = False
    self.parameterNodeSelector.baseName = "General Registration (Elastix)"
    self.parameterNodeSelector.setMRMLScene( slicer.mrmlScene )
    self.parameterNodeSelector.setToolTip( "Pick parameter set" )
    defaultParametersLayout.addRow("Parameter set: ", self.parameterNodeSelector)
        
    #
    # Inputs
    #
    inputParametersCollapsibleButton = ctk.ctkCollapsibleButton()
    inputParametersCollapsibleButton.text = "Inputs"
    self.layout.addWidget(inputParametersCollapsibleButton)

    # Layout within the dummy collapsible button
    inputParametersFormLayout = qt.QFormLayout(inputParametersCollapsibleButton)

    #
    # fixed volume selector
    #
    self.fixedVolumeSelector = slicer.qMRMLNodeComboBox()
    self.fixedVolumeSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    self.fixedVolumeSelector.selectNodeUponCreation = True
    self.fixedVolumeSelector.addEnabled = False
    self.fixedVolumeSelector.removeEnabled = False
    self.fixedVolumeSelector.noneEnabled = False
    self.fixedVolumeSelector.showHidden = False
    self.fixedVolumeSelector.showChildNodeTypes = False
    self.fixedVolumeSelector.setMRMLScene( slicer.mrmlScene )
    self.fixedVolumeSelector.setToolTip( "The moving volume will be transformed into this image space." )
    inputParametersFormLayout.addRow("Fixed volume: ", self.fixedVolumeSelector)

    #
    # moving volume selector
    #
    self.movingVolumeSelector = slicer.qMRMLNodeComboBox()
    self.movingVolumeSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    self.movingVolumeSelector.selectNodeUponCreation = True
    self.movingVolumeSelector.addEnabled = False
    self.movingVolumeSelector.removeEnabled = False
    self.movingVolumeSelector.noneEnabled = False
    self.movingVolumeSelector.showHidden = False
    self.movingVolumeSelector.showChildNodeTypes = False
    self.movingVolumeSelector.setMRMLScene( slicer.mrmlScene )
    self.movingVolumeSelector.setToolTip( "This volume will be transformed into the fixed image space" )
    inputParametersFormLayout.addRow("Moving volume: ", self.movingVolumeSelector)

    self.registrationPresetSelector = qt.QComboBox()
    for preset in RegistrationPresets:
      self.registrationPresetSelector.addItem("{0} ({1})".format(preset[RegistrationPresets_Modality], preset[RegistrationPresets_Content]))
    ##Read default settings from application settings
    # settings = qt.QSettings()
    # displayConfiguration = settings.value('SlicerHeart/DisplayConfiguration', SMALL_SCREEN)
    # displayConfigurationIndex = self.registrationPresetSelector.findData(displayConfiguration)
    # self.registrationPresetSelector.setCurrentIndex(displayConfigurationIndex) 
    inputParametersFormLayout.addRow("Preset: ", self.registrationPresetSelector)
    
    #
    # Outputs
    #
    outputParametersCollapsibleButton = ctk.ctkCollapsibleButton()
    outputParametersCollapsibleButton.text = "Outputs"
    self.layout.addWidget(outputParametersCollapsibleButton)

    # Layout within the dummy collapsible button
    outputParametersFormLayout = qt.QFormLayout(outputParametersCollapsibleButton)

    #
    # output volume selector
    #
    self.outputVolumeSelector = slicer.qMRMLNodeComboBox()
    self.outputVolumeSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    self.outputVolumeSelector.selectNodeUponCreation = True
    self.outputVolumeSelector.addEnabled = True
    self.outputVolumeSelector.removeEnabled = True
    self.outputVolumeSelector.noneEnabled = True
    self.outputVolumeSelector.showHidden = False
    self.outputVolumeSelector.showChildNodeTypes = False
    self.outputVolumeSelector.setMRMLScene( slicer.mrmlScene )
    self.outputVolumeSelector.setToolTip( "(optional) The moving image warped to the fixed image space. NOTE: You must set at least one output object (transform and/or output volume)" )
    outputParametersFormLayout.addRow("Output volume: ", self.outputVolumeSelector)

    #
    # output transform selector
    #
    self.outputTransformSelector = slicer.qMRMLNodeComboBox()
    self.outputTransformSelector.nodeTypes = ["vtkMRMLTransformNode"]
    self.outputTransformSelector.selectNodeUponCreation = True
    self.outputTransformSelector.addEnabled = True
    self.outputTransformSelector.removeEnabled = True
    self.outputTransformSelector.noneEnabled = True
    self.outputTransformSelector.showHidden = False
    self.outputTransformSelector.showChildNodeTypes = False
    self.outputTransformSelector.setMRMLScene( slicer.mrmlScene )
    self.outputTransformSelector.setToolTip( "(optional) Computed displacement field that transform nodes from moving volume space to fixed volume space. NOTE: You must set at least one output object (transform and/or output volume)." )
    outputParametersFormLayout.addRow("Output transform: ", self.outputTransformSelector)

    #
    # Advanced area
    #
    self.advancedCollapsibleButton = ctk.ctkCollapsibleButton()
    self.advancedCollapsibleButton.text = "Advanced"
    self.advancedCollapsibleButton.collapsed = True
    self.layout.addWidget(self.advancedCollapsibleButton)
    advancedFormLayout = qt.QFormLayout(self.advancedCollapsibleButton)

    self.showDetailedLogDuringExecutionCheckBox = qt.QCheckBox(" ")
    self.showDetailedLogDuringExecutionCheckBox.checked = False
    self.showDetailedLogDuringExecutionCheckBox.setToolTip("Show detailed log during registration.")
    advancedFormLayout.addRow("Show detailed log during registration:", self.showDetailedLogDuringExecutionCheckBox)

    self.deleteTemporaryFilesCheckBox = qt.QCheckBox(" ")
    self.deleteTemporaryFilesCheckBox.checked = True
    self.deleteTemporaryFilesCheckBox.setToolTip("Delete temporary files (inputs, computed outputs, logs) after the registration is completed.")

    self.showTemporaryFilesFolderButton = qt.QPushButton("Show temp folder")
    self.showTemporaryFilesFolderButton.toolTip = "Open the folder where temporary files are stored."
    self.showTemporaryFilesFolderButton.setSizePolicy(qt.QSizePolicy.MinimumExpanding, qt.QSizePolicy.Preferred)

    hbox = qt.QHBoxLayout()
    hbox.addWidget(self.deleteTemporaryFilesCheckBox)
    hbox.addWidget(self.showTemporaryFilesFolderButton)
    advancedFormLayout.addRow("Delete temporary files:", hbox)

    customElastixBinDir = self.logic.getCustomElastixBinDir()
    self.customElastixBinDirSelector = ctk.ctkPathLineEdit()
    self.customElastixBinDirSelector.filters = ctk.ctkPathLineEdit.Dirs
    self.customElastixBinDirSelector.setCurrentPath(customElastixBinDir)
    self.customElastixBinDirSelector.setSizePolicy(qt.QSizePolicy.MinimumExpanding, qt.QSizePolicy.Preferred)
    self.customElastixBinDirSelector.setToolTip("Set bin directory of an Elastix installation (where elastix executable is located). "
      "If value is empty then default elastix (bundled with SlicerElastix extension) will be used.")
    advancedFormLayout.addRow("Custom Elastix toolbox location:", self.customElastixBinDirSelector)
    
    #
    # Apply Button
    #
    self.applyButton = qt.QPushButton("Apply")
    self.applyButton.toolTip = "Run the algorithm."
    self.applyButton.enabled = False
    self.layout.addWidget(self.applyButton)

    self.statusLabel = qt.QPlainTextEdit()
    self.statusLabel.setTextInteractionFlags(qt.Qt.TextSelectableByMouse)
    self.statusLabel.setCenterOnScroll(True)
    self.layout.addWidget(self.statusLabel)

    # connections
    self.applyButton.connect('clicked(bool)', self.onApplyButton)
    self.showTemporaryFilesFolderButton.connect('clicked(bool)', self.onShowTemporaryFilesFolder)
    self.fixedVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)
    self.movingVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)
    self.outputVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)
    self.outputTransformSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)

    # Add vertical spacer
    self.layout.addStretch(1)

    # Refresh Apply button state
    self.onSelect()

  def cleanup(self):
    pass

  def onSelect(self):
    enabled = True
    if not self.fixedVolumeSelector.currentNode() or not self.movingVolumeSelector.currentNode():
      self.applyButton.text = "Select fixed and moving volumes"
      self.applyButton.enabled = False
    elif self.fixedVolumeSelector.currentNode() == self.movingVolumeSelector.currentNode():
      self.applyButton.text = "Fixed and moving volume must not be the same"
      self.applyButton.enabled = False
    elif not self.outputVolumeSelector.currentNode() and not self.outputTransformSelector.currentNode():
      self.applyButton.text = "Select an output volume and/or output transform"
      self.applyButton.enabled = False
    else:
      self.applyButton.text = "Apply"
      self.applyButton.enabled = True

  def onShowTemporaryFilesFolder(self):
    qt.QDesktopServices().openUrl(qt.QUrl("file:///" + self.logic.getTempDirectoryBase(), qt.QUrl.TolerantMode));

  def onApplyButton(self):
    if self.registrationInProgress:
      self.registrationInProgress = False
      self.logic.abortRequested = True
      self.applyButton.text = "Cancelling..."
      self.applyButton.enabled = False
      return

    self.registrationInProgress = True
    self.applyButton.text = "Cancel"
    self.statusLabel.plainText = ''
    slicer.app.setOverrideCursor(qt.Qt.WaitCursor)
    try:

      if self.customElastixBinDirSelector.currentPath:
        self.logic.setCustomElastixBinDir(self.customElastixBinDirSelector.currentPath)

      self.logic.deleteTemporaryFiles = self.deleteTemporaryFilesCheckBox.checked
      self.logic.logStandardOutput = self.showDetailedLogDuringExecutionCheckBox.checked

      parameterFilenames = RegistrationPresets[self.registrationPresetSelector.currentIndex][RegistrationPresets_ParameterFilenames]

      self.logic.registerVolumes(self.fixedVolumeSelector.currentNode(), self.movingVolumeSelector.currentNode(),
        parameterFilenames, self.outputTransformSelector.currentNode(), self.outputVolumeSelector.currentNode())
    except Exception as e:
      print e
      self.addLog("Error: {0}".format(e.message))
      import traceback
      traceback.print_exc()
    finally:
      slicer.app.restoreOverrideCursor()
      self.onSelect() # restores default Apply button state

  def addLog(self, text):
    """Append text to log window
    """
    self.statusLabel.appendPlainText(text)
    slicer.app.processEvents()  # force update

#
# ElastixLogic
#

class ElastixLogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self):
    ScriptedLoadableModuleLogic.__init__(self)
    self.logCallback = None
    self.abortRequested = False
    self.deleteTemporaryFiles = True
    self.logStandardOutput = False
    self.customElastixBinDirSettingsKey = 'Elastix/CustomElastixPath'
    import os
    self.scriptPath = os.path.dirname(os.path.abspath(__file__))
    self.registrationParameterFilesDir = os.path.abspath(os.path.join(self.scriptPath, 'Resources', 'RegistrationParameters'))
    self.elastixBinDir = None # this will be determined dynamically
    
    import platform
    executableExt = '.exe' if platform.system() == 'Windows' else ''
    self.elastixFilename = 'elastix' + executableExt
    self.transformixFilename = 'transformix' + executableExt

  def addLog(self, text):
    logging.info(text)
    if self.logCallback:
      self.logCallback(text)

  def getElastixBinDir(self):
    if self.elastixBinDir:
      return self.elastixBinDir

    self.elastixBinDir = self.getCustomElastixBinDir()
    if self.elastixBinDir:
      return self.elastixBinDir
    
    elastixBinDirCandidates = [
      # install tree
      os.path.join(self.scriptPath, '../../../bin'),
      # build tree
      os.path.join(self.scriptPath, '../../../../bin/Release'),
      os.path.join(self.scriptPath, '../../../../bin/Debug'),
      os.path.join(self.scriptPath, '../../../../bin/RelWithDebInfo'),
      os.path.join(self.scriptPath, '../../../../bin/MinSizeRel') ]
    
    for elastixBinDirCandidate in elastixBinDirCandidates:
      if os.path.isfile(os.path.join(elastixBinDirCandidate, self.elastixFilename)):
        # elastix found
        self.elastixBinDir = os.path.abspath(elastixBinDirCandidate)
        return self.elastixBinDir

    raise ValueError('Elastix not found')
  
  def getCustomElastixBinDir(self):
    settings = qt.QSettings()
    if settings.contains(self.customElastixBinDirSettingsKey):
      return slicer.util.toVTKString(settings.value(self.customElastixBinDirSettingsKey))
    return ''

  def setCustomElastixBinDir(self, customPath):
    # don't save it if already saved
    settings = qt.QSettings()
    if settings.contains(self.customElastixBinDirSettingsKey):
      if customPath == settings.value(self.customElastixBinDirSettingsKey):
        return
    settings.setValue(self.customElastixBinDirSettingsKey, customPath)
    # Update elastix bin dir
    self.elastixBinDir = None
    self.getElastixBinDir()

  def getElastixEnv(self):
    """Create an environment for elastix where executables are added to the path"""
    elastixBinDir = self.getElastixBinDir()
    elastixEnv = os.environ.copy()
    elastixEnv["PATH"] = elastixBinDir + os.pathsep + elastixEnv["PATH"]
    
    import platform
    if platform.system() != 'Windows':
      elastixLibDir = os.path.abspath(os.path.join(elastixBinDir, '../lib'))
      elastixEnv["LD_LIBRARY_PATH"] = elastixLibDir + os.pathsep + elastixEnv["LD_LIBRARY_PATH"]
    
    return elastixEnv
  
  def getRegistrationPresets(self):
    presets = []
    presets.append({ 'id': 'par000', 'name': 'Default', 'modality': 'all', 'content': 'all', 'parameterFiles': ['Par0000affine.txt', 'Par0000bspline.txt'] })
    presets.append({ 'id': 'par001', 'name': 'Brain MR T1', 'modality': '3D MR T1, monomodal', 'content': 'brain', 'parameterFiles': ['Par0001affine.txt', 'Par0001bspline.txt']})
    presets.append({ 'id': 'par002', 'name': 'Prostate MR', 'modality': '3D MR BFFE, monomodal', 'content': 'prostate', 'parameterFiles': ['Par0002affine.txt', 'Par0002bspline.txt']})
    return presets

  def startElastix(self, cmdLineArguments):
    self.addLog("Register volumes...")
    import subprocess
    executableFilePath = os.path.join(self.getElastixBinDir(),self.elastixFilename)
    logging.info("Register volumes using: "+executableFilePath+": "+repr(cmdLineArguments))
    return subprocess.Popen([executableFilePath] + cmdLineArguments, env=self.getElastixEnv(),
                            stdout=subprocess.PIPE, universal_newlines=True)

  def startTransformix(self, cmdLineArguments):
    self.addLog("Generate output...")
    import subprocess
    executableFilePath = os.path.join(self.getElastixBinDir(), self.transformixFilename)
    logging.info("Generate output using: " + executableFilePath + ": " + repr(cmdLineArguments))
    return subprocess.Popen([os.path.join(self.getElastixBinDir(),self.transformixFilename)] + cmdLineArguments, env=self.getElastixEnv(),
                            stdout=subprocess.PIPE, universal_newlines = True)

  def logProcessOutput(self, process):
    # save process output (if not logged) so that it can be displayed in case of an error
    processOutput = ''
    import subprocess
    for stdout_line in iter(process.stdout.readline, ""):
      if self.logStandardOutput:
        self.addLog(stdout_line.rstrip())
      else:
        processOutput += stdout_line.rstrip() + '\n'
      slicer.app.processEvents()  # give a chance to click Cancel button
      if self.abortRequested:
        process.kill()
    process.stdout.close()
    return_code = process.wait()
    if return_code:
      if self.abortRequested:
        raise ValueError("User requested cancel.")
      else:
        if processOutput:
          self.addLog(processOutput)
        raise subprocess.CalledProcessError(return_code, "elastix")

  def getTempDirectoryBase(self):
    tempDir = qt.QDir(slicer.app.temporaryPath)
    fileInfo = qt.QFileInfo(qt.QDir(tempDir), "Elastix")
    dirPath = fileInfo.absoluteFilePath()
    qt.QDir().mkpath(dirPath)
    return dirPath

  def createTempDirectory(self):
    import qt, slicer
    tempDir = qt.QDir(self.getTempDirectoryBase())
    tempDirName = qt.QDateTime().currentDateTime().toString("yyyy-MM-dd_hh+mm+ss.zzz")
    fileInfo = qt.QFileInfo(qt.QDir(tempDir), tempDirName)
    dirPath = fileInfo.absoluteFilePath()
    qt.QDir().mkpath(dirPath)
    return dirPath 
  
  def registerVolumes(self, fixedVolumeNode, movingVolumeNode, parameterFilenames, outputTransformNode, outputVolumeNode):
    self.abortRequested = False
    tempDir = self.createTempDirectory()
    self.addLog('Volume registration is started in working directory: '+tempDir)

    # Write inputs
    inputDir = os.path.join(tempDir, 'input')
    qt.QDir().mkpath(inputDir)
    fixedVolumePath = os.path.join(inputDir, "fixed.mha")
    movingVolumePath = os.path.join(inputDir, "moving.mha")
    slicer.util.saveNode(fixedVolumeNode, fixedVolumePath, {"useCompression": False})
    slicer.util.saveNode(movingVolumeNode, movingVolumePath, {"useCompression": False})

    # Run registration
    resultTransformDir = os.path.join(tempDir, 'result-transform')
    qt.QDir().mkpath(resultTransformDir)    
    inputParamsElastix = ['-f', fixedVolumePath, '-m', movingVolumePath, '-out', resultTransformDir]
    for parameterFilename in parameterFilenames:
      inputParamsElastix.append('-p')
      parameterFilePath = os.path.abspath(os.path.join(self.registrationParameterFilesDir, parameterFilename))
      inputParamsElastix.append(parameterFilePath)
    ep = self.startElastix(inputParamsElastix)
    self.logProcessOutput(ep)

    # Resample
    if not self.abortRequested:
      resultResampleDir = os.path.join(tempDir, 'result-resample')
      qt.QDir().mkpath(resultResampleDir)
      inputParamsTransformix = ['-in', movingVolumePath, '-out', resultResampleDir]
      if outputTransformNode:
        inputParamsTransformix += ['-def', 'all']
      if outputVolumeNode:
        inputParamsTransformix += ['-tp', resultTransformDir+'/TransformParameters.'+str(len(parameterFilenames)-1)+'.txt']
      tp = self.startTransformix(inputParamsTransformix)
      self.logProcessOutput(tp)

    # Write results
    if not self.abortRequested:

      if outputVolumeNode:
        outputVolumePath = os.path.join(resultResampleDir, "result.mhd")
        [success, loadedOutputVolumeNode] = slicer.util.loadVolume(outputVolumePath, returnNode = True)
        if success:
          outputVolumeNode.SetAndObserveImageData(loadedOutputVolumeNode.GetImageData())
          ijkToRas = vtk.vtkMatrix4x4()
          loadedOutputVolumeNode.GetIJKToRASMatrix(ijkToRas)
          outputVolumeNode.SetIJKToRASMatrix(ijkToRas)
          slicer.mrmlScene.RemoveNode(loadedOutputVolumeNode)

      if outputTransformNode:
        outputTransformPath = os.path.join(resultResampleDir, "deformationField.mhd")
        [success, loadedOutputTransformNode] = slicer.util.loadTransform(outputTransformPath, returnNode = True)
        if success:
          if loadedOutputTransformNode.GetReadAsTransformToParent():
            outputTransformNode.SetAndObserveTransformToParent(loadedOutputTransformNode.GetTransformToParent())
          else:
            outputTransformNode.SetAndObserveTransformFromParent(loadedOutputTransformNode.GetTransformFromParent())
          slicer.mrmlScene.RemoveNode(loadedOutputTransformNode)

    # Clean up
    if self.deleteTemporaryFiles:
      import shutil
      shutil.rmtree(tempDir)
      
    self.addLog("Registration is completed")

class ElastixTest(ScriptedLoadableModuleTest):
  """
  This is the test case for your scripted module.
  Uses ScriptedLoadableModuleTest base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear(0)

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_Elastix1()

  def test_Elastix1(self):
    """ Ideally you should have several levels of tests.  At the lowest level
    tests should exercise the functionality of the logic with different inputs
    (both valid and invalid).  At higher levels your tests should emulate the
    way the user would interact with your code and confirm that it still works
    the way you intended.
    One of the most important features of the tests is that it should alert other
    developers when their changes will have an impact on the behavior of your
    module.  For example, if a developer removes a feature that you depend on,
    your test should break so they know that the feature is needed.
    """

    self.delayDisplay("Starting the test")
    #
    # first, get some data
    #
    
    import SampleData
    sampleDataLogic = SampleData.SampleDataLogic()
    tumor1 = sampleDataLogic.downloadMRBrainTumor1()
    tumor2 = sampleDataLogic.downloadMRBrainTumor2()

    outputVolume = slicer.vtkMRMLScalarVolumeNode()
    slicer.mrmlScene.AddNode(outputVolume)
    outputVolume.CreateDefaultDisplayNodes()
    
    logic = ElastixLogic()       
    parameterFilenames = RegistrationPresets[0][RegistrationPresets_ParameterFilenames]
    logic.registerVolumes(tumor1, tumor2, parameterFilenames, None, outputVolume)
    
    self.delayDisplay('Test passed!')


RegistrationPresets_Id = 0
RegistrationPresets_Modality = 1
RegistrationPresets_Content = 2
RegistrationPresets_Description = 3
RegistrationPresets_Publications = 4
RegistrationPresets_ParameterFilenames = 5

RegistrationPresets = [
[ "default0", "generic", "all", "'default' parameter files for starting elastix users", "", ["parameters_Rigid.txt", "parameters_BSpline.txt"]],
[ "par0000", "3D MR T1, monomodal", "brain", "interpatient; affine + B-spline transformation; mutual information", "van der Lijn (2009) - Cerebellum Segmentation in MRI Using Atlas Registration and Local Multi-Scale Image Descriptors", ["Par0000affine.txt", "Par0000bspline.txt"]],
[ "par0001", "3D MR BFFE, monomodal", "prostate", "interpatient; several transformation models; localised mutual information", "Klein & Staring (2010) - elastix: a toolbox for intensity-based medical image registration", [ "Par0001translation.txt", "Par0001bspline16.txt"]],
[ "par0002", "3D MR T1 & PET", "brain", "intrapatient; translation; mutual information", "Klein & Staring (2010) - elastix: a toolbox for intensity-based medical image registration", ["Par0002.fs.MI.rigid.RandomCoordinate.txt"]],
[ "par0003", "3D CT, monomodal", "lung", "interpatient; affine + B-spline transformation; mutual information", "Klein & Staring (2010) - elastix: a toolbox for intensity-based medical image registration", ["Par0003.affine.txt", "Par0003.bs-R4-fg.txt"]],
#[ "par0004", "3D CT, monomodal", "lung", "intrapatient; rigid + B-spline transformation; mutual information", "Staring (2007) - A Rigidity Penalty Term for Nonrigid Registration"],
#[ "par0005", "3D MR T2, monomodal", "cervix", "intrapatient; rigid + B-spline transformation; multi-feature &alpha;-mutual information", "Staring (2009) - Registration of Cervical MRI Using Multifeature Mutual Information"],
#[ "par0006", "3D MR T2*, histology", "tumor", "rigid + B-spline transformation; multi-feature &alpha;-mutual information", "Alic (2011) - Facilitating tumor functional assessment by spatially relating 3D tumor histology and in vivo MRI: Image registration approach"],
#[ "par0007", "4D CT, monomodal", "lung", "intrapatient; B-spline transformation; mutual information", "Ding (2010) - 4DCT-Based Measurement of Radiation Induced Changes in Pulmonary Function", ["Parameters.MI.Coarse.Bspline_tuned.txt", "Parameters.MI.Fine.Bspline_tuned.txt", "Parameters.MI.RP.Bspline_tuned.txt"]],
[ "par0008", "3D CT, monomodal", "lung", "intrapatient; B-spline transformation; mutual information", "Murphy (2008) - Semi-Automatic Reference Standard Construction for Quantitative Evaluation of Lung CT Registration", ["Parameters.Par0008.affine.txt", "Parameters.Par0008.elastic.txt"]],
[ "par0009", "3D MRI, monomodal", "brain", "interpatient; B-spline transformation; mutual information", "Artaechevarria (2009) - Combination strategies in multi-atlas image segmentation: application to brain MR data", ["Parameters.Par0009.affine.txt", "Parameters.Par0009.elastic.txt"]],
[ "par0010", "3D MR HASTE, monomodal", "brain", "interpatient; affine + B-spline transformation; mutual information", "Klein (2010) - Early diagnosis of dementia based on intersubject whole-brain dissimilarities", ["Par0010affine.txt", "Par0010bspline.txt"]],
[ "par0011", "3D CT, monomodal", "lung", "intrapatient (sometimes intra-sheep); B-spline transformation; normalized correlation", "Staring (2010), Pulmonary Image Registration With <tt>elastix</tt> Using a Standard Intensity-Based Algorithm", ["Parameters.Par0011.affine.txt", "Parameters.Par0011.bspline1_s.txt", "Parameters.Par0011.bspline2_s.txt"]],
#[ "par0012", "4D CT(A), 3D MR, 3D US, 3D synthetic, monomodal", "heart, lung, carotid", "motion estimation; (cyclic) B-spline transformation; variance over last dimension", "Metz (2011), Nonrigid registration of dynamic medical imaging data using nD+t B-splines and a groupwise optimization approach"],
[ "par0013", "2D x-ray - 3D CT ", "cerebral", "registration of interventional x-ray data to 3D CT for motion estimation, patient positioning or image guidance", "van der Bom (2011), Evaluation of optimization methods for intensity-based 2D-3D registration in x-ray guided interventions", ["par0013Powel_NGC_singleImage.txt"]],
[ "par0014", "3D microCT", "whole-body mouse", "intra-mouse; B-spline transformation; combination of normalized correlation and the Euclidean distance metric", "Baiker (2011), Automated Registration of Whole-Body Follow-Up MicroCT Data of Mice", ["Parameters.similarity.txt", "Parameters.NCC.txt"]],
[ "par0015", "3D CT, monomodal", "lung", "intrapatient; B-spline transformation; several similarity metrics", "Staring (2013), Towards Local Progression Estimation of Pulmonary Emphysema using CT", ["Parameters.Par0015.expA.patient.NC.affine.txt", "Parameters.Par0015.expA.patient.NC.bspline.txt" ]],
#[ "par0016", "3D CT, monomodal", "lung", "intrapatient; Multi B-spline transformation; sliding motion", "Delmon (2011), Direction dependent B-splines decomposition for the registration of sliding objects"],
[ "par0017", "3D MR, monomodal", "knee cartilage", "intrapatient; rigid; localized mutual information", "Bron (2013) -  Image registration improves human knee cartilage T1 mapping with delayed Gadolinium Enhanced MRI of Cartilage (dGEMRIC)", ["Par0017_cartilage_RigidLMI.txt"]],
[ "par0018", "3D MR, multi sequence", "carotid artery", "interpatient; several transformation models; mutual information based similarity metrics", "van 't Klooster - Automated Registration of Multispectral MR Vessel Wall Images of the Carotid Artery", ["Par0018_3D_rigid_MI.txt", "Par0018_3D_affine_MI.txt", "Par0018_3D_bspline_MI_15.txt"]],
[ "par0019", "3D CT, monomodal", "head and neck", "inter patient; rigid and B-spline transformation, advanced mean square and normalized correlation metrics", "Fortunati (2013) - Atlas based segmentation for hyperthermia treatment planning", ["Parameters_RigidAMS.txt", "Parameters_BSplineNCC.txt"]],
[ "par0020", "3D MR, multi-contrast", "rat brain", "intra-subject, longitudinal data; rigid + affine + B-spline transformation, advanced normalized correlation metric with a transform bending energy penalty", "Khmelinskii (2013) - [http://proceedings.spiedigitallibrary.org/proceeding.aspx?articleid=1674633 A visualization platform for high-throughput, follow-up, co-registered multi-contrast MRI rat brain data. Mengler (2014) - [http://www.sciencedirect.com/science/article/pii/S1053811913008963 Brain maturation of the adolescent rat cortex and striatum: changes in volume and myelination]", ["Par0020rigid.txt", "Par0020affine.txt", "Par0020bspline2.txt" ]],
#[ "par0021", "DT-MRI", "brain", "Registration optimisation for subject-FA images to FA template, multiple data sources", "De Groot (2013), Improving alignment in Tract-based spatial statistics: Evaluation and optimization of image registration"],
#[ "par0022", "3D MR T2, monomodal", "cervix", "intrapatient; rigid + B-spline transformation; statistical shape regularization", "Berendsen (2013), Free-form image registration regularized by a statistical shape model: application to organ segmentation in cervical MR"],
[ "par0023", "3D CT, 3D MR, multimodal", "head and neck", "intrapatient; rigid + B-spline transformation; localized mutual information combined with bending energy penalty", "Leibfarth (2013),  A strategy for multimodal deformable image registration to integrate PET/MR into radiotherapy treatment planning", ["Rigid.txt", "Deformable.txt"]],
#[ "par0024", "3D MR T2, monomodal", "cervix", "interpatient; rigid + B-spline transformation; missing structure penalty", "Berendsen (2014), Registration of structurally dissimilar images in MRI-based brachytherapy"],
[ "par0025", "3D MR, multi-contrast", "mouse brain", "intra-subject, longitudinal data; rigid + affine + B-spline transformation, advanced normalized correlation metric with a transform bending energy penalty|| Hammelrath (2015) - [http://www.sciencedirect.com/science/article/pii/S1053811915009039 Morphological maturation of the mouse brain: an ''in vivo'' MRI and histology investigation]", ["Par0025rigid.txt", "Par0025affine.txt", "Par0025bspline.txt"]],
[ "par0026", "3D MR, multi-contrast", "rat brain", "intra-subject, longitudinal data; rigid + affine + B-spline transformation", " Hammelrath (2016)", ["Par0026rigid.txt", "Par0026affine.txt", "Par0026bspline.txt"]],
#[ "par0027", "3D CT, 3D MR, multimodal, multi sequence", "head and neck", "intra patient; rigid + B-spline transformation; mutual information, multi parametric mutual information", "Fortunati (2014),  Feasibility of Multimodal Deformable Registration for Head and Neck Tumor Treatment Planning"],
#[ "par0028", "3D CT, monomodal", "head and neck", "intra patient; rigid + B-spline transformation; several B-pline knot spacings; synthesized head and neck phantoms", "Brouwer (2014),  The effects of CT image characteristics and knot spacing on the spatial accuracy of B-spline deformable image registration in the head and neck geometry"],
#[ "par0029", "3D diffusion-weighted MR images (DW-MRI)", "abdomen", "intra patient; B-spline transformation; mutual information", "Guyader (2014) - Influence of image registration on apparent diffusion coefficient images computed from free-breathing diffusion MR images of the abdomen"],
[ "par0030", "3D T1 fat-suppressed Ga-enhanced extremity MR", "wrist", "inter patient; Affine + B-spline transformation; normalized cross correlation. intra patient; Rigid transformation; mutual information", "Roex - MSc thesis: Early Detection of Rheumatoid Arthritis using extremity MRI: Quantification of Bone Marrow Edema in the Carpal bones", ["Parameters0030_Euler.txt", "Parameters0030_Affine.txt", "Parameters0030_Bspline.txt"]],
#[ "par0031", "3D CT, monomodal", "thorax", "intrapatient; regional-independent B-spline transformation; sliding surface penalty", "Berendsen (2014), Registration of organs with sliding interfaces and changing topologies"],
[ "par0032", "3D DCE-MRI", "breast", "intrapatient; rigid + B-spline transformation; mutual information", "Gubern-Merida (2015), Automated localization of breast cancer in DCE-MRI", ["Par0032_rigid.txt", "Par0032_bsplines.txt"]],
[ "par0033", "3D MR", "mouse brain", "inter-subject; rigid + affine + B-spline transformation; mutual information metric with a transform bending energy penalty", "Bink (2016), Kogelman (2016)", ["Par0033rigid.txt", "Par0033similarity.txt", "Par0033bspline.txt"]],
[ "par0034", "2D CBF MR", "mouse brain", "inter-subject; rigid + affine + B-spline transformation; advanced normalized correlation + mutual information metric with a transform bending energy penalty", "Bink (2016)", ["Par0034rigid.txt", "Par0034affine.txt", "Par0034bspline.txt"]],
#[ "par0035", "CT, MR, ultrasound", "brain, lung, abdomen", "intra-subject, inter-subject; mono-modal and multi-modal; rigid, affine and B-spline transformations; mean square difference, normalized correlation, mutual information", "Qiao (2015), Fast Automatic Step Size Estimation for Gradient Descent Optimization of Image Registration"],
#[ "par0036", "MRI joint histograms", "whole-body", "intra-subject, inter-station; affine; normalized correlation", "Dzyubachyk (2015)"],
#[ "par0037", "DTS", "lung", "intra-subject; translational registration; mutual information", "You (2015)"],
#[ "par0038", "MRI", "mouse brain stroke", "intra-subject, longitudinal data; rigid + affine + B-spline transformation, advanced normalized correlation metric with a transform bending energy penalty", "Mulder, Khmelinskii, Dzyubachyk (2016)"],
#[ "par0039", "quantitative MRI", "porcine heart, abdomen, carotid, brain", "intra-subject; affine or B-spline transformation; groupwise registration; PCA metrics", "Huizinga (2016), PCA-based groupwise image registration for quantitative MRI"],
[ "par0040", "extremity MRI", "wrist", "intra-subject; affine transformation, mutual information metric", "Aizenberg (2016)", ["Par0040affine.txt"]],
[ "par0041", "extremity MRI", "wrist", "inter-subject; similarity + B-spline transformation, advanced normalized correlation metric", "Aizenberg (2016)", ["Par0041similarity.txt", "Par0041bspline.txt"]],
[ "par0042", "MRI", "spine", "inter-subject; rigid + B-spline transformation, advanced normalized correlation metric", "Aizenberg (2016)", ["Par0042rigid.txt", "Par0042bspline.txt"]],
[ "par0043", "CT/ MR-based pseudo-CT", "pelvis (prostate)", "intra-subject; multi-resolution (4), rigid + B-spline transformation, Mutual Information metric (Mattes) with Adaptive Stochastic Gradient Descent optimizer", "Maspero M, et al. (2017), [http://iopscience.iop.org/article/10.1088/1361-6560/aa4fe7 Quantification of confounding factors in MRI-based dose calculations as applied to prostate IMRT.] Phys Med Biol. 62(3)", ["Par0043rigid.txt"]],
[ "par0044", "3D CT, multi-contrast ", "cardiac", "intra-subject; multi-image; affine (Mutual Information) + multi-image B-spline transformation (Mutual Information and mean square difference); ", "Giordano (2016)", ["Par0044Affine.txt", "Par0044NonRigid.txt"]],
#[ "par0045", " MRI", "mouse brain", "inter and intra-subject, perfusion data; rigid + affine + B-spline transformation; ", "Hirschler and Munting (2016)"]
]
