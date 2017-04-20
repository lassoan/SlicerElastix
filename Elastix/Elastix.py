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
    for preset in self.logic.getRegistrationPresets():
      self.registrationPresetSelector.addItem("{0} ({1})".format(preset[RegistrationPresets_Modality], preset[RegistrationPresets_Content]))
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

    self.keepTemporaryFilesCheckBox = qt.QCheckBox(" ")
    self.keepTemporaryFilesCheckBox.checked = False
    self.keepTemporaryFilesCheckBox.setToolTip("Keep temporary files (inputs, computed outputs, logs) after the registration is completed.")

    self.showTemporaryFilesFolderButton = qt.QPushButton("Show temp folder")
    self.showTemporaryFilesFolderButton.toolTip = "Open the folder where temporary files are stored."
    self.showTemporaryFilesFolderButton.setSizePolicy(qt.QSizePolicy.MinimumExpanding, qt.QSizePolicy.Preferred)

    hbox = qt.QHBoxLayout()
    hbox.addWidget(self.keepTemporaryFilesCheckBox)
    hbox.addWidget(self.showTemporaryFilesFolderButton)
    advancedFormLayout.addRow("Keep temporary files:", hbox)

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

      self.logic.deleteTemporaryFiles = not self.keepTemporaryFilesCheckBox.checked
      self.logic.logStandardOutput = self.showDetailedLogDuringExecutionCheckBox.checked

      parameterFilenames = self.logic.getRegistrationPresets()[self.registrationPresetSelector.currentIndex][RegistrationPresets_ParameterFilenames]

      self.logic.registerVolumes(self.fixedVolumeSelector.currentNode(), self.movingVolumeSelector.currentNode(),
        parameterFilenames, self.outputTransformSelector.currentNode(), self.outputVolumeSelector.currentNode())
    except Exception as e:
      print e
      self.addLog("Error: {0}".format(e.message))
      import traceback
      traceback.print_exc()
    finally:
      slicer.app.restoreOverrideCursor()
      self.registrationInProgress = False
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
    self.registrationPresets = None
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
    if self.registrationPresets:
      return self.registrationPresets

    # Read database from XML file
    elastixParameterSetDatabasePath = os.path.join(self.scriptPath, 'Resources', 'RegistrationParameters', 'ElastixParameterSetDatabase.xml')
    if not os.path.isfile(elastixParameterSetDatabasePath):
      raise ValueError("Failed to open parameter set database: "+elastixParameterSetDatabasePath)
    elastixParameterSetDatabaseXml = vtk.vtkXMLUtilities.ReadElementFromFile(elastixParameterSetDatabasePath)
    elastixParameterSetDatabaseXml.UnRegister(None)
    
    # Create python list from XML for convenience
    self.registrationPresets = []
    for parameterSetIndex in range(elastixParameterSetDatabaseXml.GetNumberOfNestedElements()):
      parameterSetXml = elastixParameterSetDatabaseXml.GetNestedElement(parameterSetIndex)
      parameterFilesXml = parameterSetXml.FindNestedElementWithName('ParameterFiles')
      parameterFiles = []
      for parameterFileIndex in range(parameterFilesXml.GetNumberOfNestedElements()):
        parameterFiles.append(parameterFilesXml.GetNestedElement(parameterFileIndex).GetAttribute('Name'))
      self.registrationPresets.append([parameterSetXml.GetAttribute('id'), parameterSetXml.GetAttribute('modality'),
        parameterSetXml.GetAttribute('content'), parameterSetXml.GetAttribute('description'), parameterSetXml.GetAttribute('publications'), parameterFiles])

    return self.registrationPresets

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
    parameterFilenames = logic.getRegistrationPresets()[0][RegistrationPresets_ParameterFilenames]
    logic.registerVolumes(tumor1, tumor2, parameterFilenames, None, outputVolume)
    
    self.delayDisplay('Test passed!')


RegistrationPresets_Id = 0
RegistrationPresets_Modality = 1
RegistrationPresets_Content = 2
RegistrationPresets_Description = 3
RegistrationPresets_Publications = 4
RegistrationPresets_ParameterFilenames = 5
