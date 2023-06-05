from __future__ import print_function
import os
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
import logging
import sys

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
    self.parent.contributors = ["Andras Lasso (PerkLab - Queen's University), Christian Herz (CHOP)"]
    self.parent.helpText = """Align volumes based on image content using <a href="http://elastix.isi.uu.nl/">Elastix medical image registration toolbox</a>.
<p>Registration troubleshooting: check "Keep temporary files" option before starting regsitration and click on "Show temp folder" to open the folder that contains detailed logs.
<p>Edit registration parameters: open Advanced section, click "Show database folder", and edit presets. To add a new preset or modify registration phases, modify ElastixParameterSetDatabase.xml.
See <a href="http://elastix.bigr.nl/wiki/index.php/Parameter_file_database">registration parameter set database</a> and <a href="http://elastix.isi.uu.nl/doxygen/index.html">Elastix documentation</a> for more details."""
    self.parent.acknowledgementText = """
This module was originally developed by Andras Lasso (Queen's University, PerkLab)
to serve as a frontend to Elastix medical image registration toolbox.
If you use this module, please cite the following articles:
<ul><li>S. Klein, M. Staring, K. Murphy, M.A. Viergever, J.P.W. Pluim, "<a href="http://elastix.isi.uu.nl/marius/publications/2010_j_TMI.php">elastix: a toolbox for intensity based medical image registration</a>", IEEE Transactions on Medical Imaging, vol. 29, no. 1, pp. 196 - 205, January 2010.</li>
<li>D.P. Shamonin, E.E. Bron, B.P.F. Lelieveldt, M. Smits, S. Klein and M. Staring, "<a href="http://elastix.isi.uu.nl/marius/publications/2014_j_FNI.php">Fast Parallel Image Registration on CPU and GPU for Diagnostic Classification of Alzheimer's Disease</a>", Frontiers in Neuroinformatics, vol. 7, no. 50, pp. 1-15, January 2014.</li></ul>
See more information about Elastix medical image registration toolbox at <a href="http://elastix.isi.uu.nl/">http://elastix.isi.uu.nl/</a>.
"""

#
# ElastixWidget
#

class ElastixWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent=None):
    """
    Called when the user opens the module the first time and the widget is initialized.
    """
    ScriptedLoadableModuleWidget.__init__(self, parent)
    VTKObservationMixin.__init__(self)  # needed for parameter node observation
    self._parameterNode = None
    self._updatingGUIFromParameterNode = False

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)

    self.logic = ElastixLogic()
    self.logic.logCallback = self.addLog
    self.registrationInProgress = False

    # Instantiate and connect widgets ...

    # Load widget from .ui file (created by Qt Designer).
    # Additional widgets can be instantiated manually and added to self.layout.
    uiWidget = slicer.util.loadUI(self.resourcePath('UI/Elastix.ui'))
    self.layout.addWidget(uiWidget)
    self.ui = slicer.util.childWidgetVariables(uiWidget)

    self.ui.parameterNodeSelector.addAttribute("vtkMRMLScriptedModuleNode", "ModuleName", self.moduleName)
    self.ui.parameterNodeSelector.setNodeTypeLabel("ElastixParameters", "vtkMRMLScriptedModuleNode")

    self.ui.parameterNodeSelector.setMRMLScene(slicer.mrmlScene)
    self.ui.fixedVolumeSelector.setMRMLScene(slicer.mrmlScene)
    self.ui.movingVolumeSelector.setMRMLScene(slicer.mrmlScene)
    self.ui.fixedVolumeMaskSelector.setMRMLScene(slicer.mrmlScene)
    self.ui.movingVolumeMaskSelector.setMRMLScene(slicer.mrmlScene)
    self.ui.outputVolumeSelector.setMRMLScene(slicer.mrmlScene)
    self.ui.outputTransformSelector.setMRMLScene(slicer.mrmlScene)
    self.ui.initialTransformSelector.setMRMLScene(slicer.mrmlScene)

    for preset in self.logic.getRegistrationPresets():
      self.ui.registrationPresetSelector.addItem(
        f"{preset[RegistrationPresets_Modality]} ({preset[RegistrationPresets_Content]})"
      )

    self.ui.customElastixBinDirSelector.settingKey = self.logic.customElastixBinDirSettingsKey
    self.ui.customElastixBinDirSelector.retrieveHistory()
    self.ui.customElastixBinDirSelector.currentPath = ''
    self.ui.customElastixBinDirSelector.currentPathChanged.connect(self.onCustomElastixBinDirChanged)

    # connections

    # These connections ensure that we update parameter node when scene is closed
    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)

    self.ui.applyButton.connect('clicked(bool)', self.onApplyButton)
    self.ui.showTemporaryFilesFolderButton.connect('clicked(bool)', self.onShowTemporaryFilesFolder)
    self.ui.showRegistrationParametersDatabaseFolderButton.connect('clicked(bool)',
                                                                   self.onShowRegistrationParametersDatabaseFolder)
    self.ui.parameterNodeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.setParameterNode)

    self.ui.fixedVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateParameterNodeFromGUI)
    self.ui.movingVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateParameterNodeFromGUI)
    self.ui.fixedVolumeMaskSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateParameterNodeFromGUI)
    self.ui.movingVolumeMaskSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateParameterNodeFromGUI)
    self.ui.outputVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateParameterNodeFromGUI)
    self.ui.outputTransformSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateParameterNodeFromGUI)
    self.ui.initialTransformSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateParameterNodeFromGUI)
    self.ui.forceDisplacementFieldOutputCheckbox.toggled.connect(self.updateParameterNodeFromGUI)
    self.ui.registrationPresetSelector.currentIndexChanged.connect(self.updateParameterNodeFromGUI)
    # Immediately update deleteTemporaryFiles in the logic to make it possible to decide to
    # keep the temporary file while the registration is running
    self.ui.keepTemporaryFilesCheckBox.connect("toggled(bool)", self.onKeepTemporaryFilesToggled)

    self.initializeParameterNode()

  def cleanup(self):
    self.removeObservers()

  def enter(self):
    self.initializeParameterNode()

  def exit(self):
    self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)

  def onSceneStartClose(self, caller, event):
    self.setParameterNode(None)

  def onSceneEndClose(self, caller, event):
    if self.parent.isEntered:
      self.initializeParameterNode()

  def initializeParameterNode(self):
    self.setParameterNode(self.logic.getParameterNode())

  def setParameterNode(self, inputParameterNode):
    if inputParameterNode:
      self.logic.setDefaultParameters(inputParameterNode)

    # Unobserve previously selected parameter node and add an observer to the newly selected.
    # Changes of parameter node are observed so that whenever parameters are changed by a script or any other module
    # those are reflected immediately in the GUI.
    if self._parameterNode is not None and self.hasObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent,
                                                            self.updateGUIFromParameterNode):
      self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)
    self._parameterNode = inputParameterNode
    if self._parameterNode is not None:
      self.addObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)

    wasBlocked = self.ui.parameterNodeSelector.blockSignals(True)
    self.ui.parameterNodeSelector.setCurrentNode(self._parameterNode)
    self.ui.parameterNodeSelector.blockSignals(wasBlocked)

    # Initial GUI update
    self.updateGUIFromParameterNode()

  def updateParameterNodeFromGUI(self, caller=None, event=None):
    """
    This method is called when the user makes any change in the GUI.
    The changes are saved into the parameter node (so that they are restored when the scene is saved and loaded).
    """

    if self._parameterNode is None or self._updatingGUIFromParameterNode:
      return

    wasModified = self._parameterNode.StartModify()  # Modify all properties in a single batch

    self._parameterNode.SetNodeReferenceID(self.logic.FIXED_VOLUME_REF, self.ui.fixedVolumeSelector.currentNodeID)
    self._parameterNode.SetNodeReferenceID(self.logic.MOVING_VOLUME_REF, self.ui.movingVolumeSelector.currentNodeID)
    self._parameterNode.SetNodeReferenceID(self.logic.FIXED_VOLUME_MASK_REF, self.ui.fixedVolumeMaskSelector.currentNodeID)
    self._parameterNode.SetNodeReferenceID(self.logic.MOVING_VOLUME_MASK_REF, self.ui.movingVolumeMaskSelector.currentNodeID)
    self._parameterNode.SetNodeReferenceID(self.logic.OUTPUT_VOLUME_REF, self.ui.outputVolumeSelector.currentNodeID)
    self._parameterNode.SetNodeReferenceID(self.logic.OUTPUT_TRANSFORM_REF, self.ui.outputTransformSelector.currentNodeID)
    self._parameterNode.SetNodeReferenceID(self.logic.INITIAL_TRANSFORM_REF, self.ui.initialTransformSelector.currentNodeID)
    self._parameterNode.SetParameter(self.logic.FORCE_GRID_TRANSFORM_PARAM, str(self.ui.forceDisplacementFieldOutputCheckbox.checked))

    registrationPreset = self.logic.getRegistrationPresets()[self.ui.registrationPresetSelector.currentIndex]
    self._parameterNode.SetParameter(self.logic.REGISTRATION_PRESET_ID_PARAM, registrationPreset[RegistrationPresets_Id])

    self._parameterNode.EndModify(wasModified)

  def updateGUIFromParameterNode(self, caller=None, event=None):
    """
    This method is called whenever parameter node is changed.
    The module GUI is updated to show the current state of the parameter node.
    """
    if self._parameterNode is None or self._updatingGUIFromParameterNode:
      return

    # Make sure GUI changes do not call updateParameterNodeFromGUI (it could cause infinite loop)
    self._updatingGUIFromParameterNode = True

    fixedVolumeNode = self._parameterNode.GetNodeReference(self.logic.FIXED_VOLUME_REF)
    self.ui.fixedVolumeSelector.setCurrentNode(fixedVolumeNode)

    movingVolumeNode = self._parameterNode.GetNodeReference(self.logic.MOVING_VOLUME_REF)
    self.ui.movingVolumeSelector.setCurrentNode(movingVolumeNode)
    self.ui.fixedVolumeMaskSelector.setCurrentNode(self._parameterNode.GetNodeReference(self.logic.FIXED_VOLUME_MASK_REF))
    self.ui.movingVolumeMaskSelector.setCurrentNode(self._parameterNode.GetNodeReference(self.logic.MOVING_VOLUME_MASK_REF))

    outputVolumeNode = self._parameterNode.GetNodeReference(self.logic.OUTPUT_VOLUME_REF)
    self.ui.outputVolumeSelector.setCurrentNode(outputVolumeNode)

    outputTransformNode = self._parameterNode.GetNodeReference(self.logic.OUTPUT_TRANSFORM_REF)
    self.ui.outputTransformSelector.setCurrentNode(outputTransformNode)

    self.ui.initialTransformSelector.setCurrentNode(self._parameterNode.GetNodeReference(self.logic.INITIAL_TRANSFORM_REF))

    self.ui.forceDisplacementFieldOutputCheckbox.checked = \
      slicer.util.toBool(self._parameterNode.GetParameter(self.logic.FORCE_GRID_TRANSFORM_PARAM))

    registrationPresetIndex = \
      self.logic.getRegistrationIndexByPresetId(self._parameterNode.GetParameter(self.logic.REGISTRATION_PRESET_ID_PARAM))
    self.ui.registrationPresetSelector.setCurrentIndex(registrationPresetIndex)

    if not fixedVolumeNode or not movingVolumeNode:
      self.ui.applyButton.text = "Select fixed and moving volumes"
      self.ui.applyButton.enabled = False
    elif fixedVolumeNode == movingVolumeNode:
      self.ui.applyButton.text = "Fixed and moving volume must not be the same"
      self.ui.applyButton.enabled = False
    elif not outputVolumeNode and not outputTransformNode:
      self.ui.applyButton.text = "Select an output volume and/or output transform"
      self.ui.applyButton.enabled = False
    else:
      self.ui.applyButton.text = "Apply"
      self.ui.applyButton.enabled = True

    # All the GUI updates are done
    self._updatingGUIFromParameterNode = False

  def onShowTemporaryFilesFolder(self):
    qt.QDesktopServices().openUrl(qt.QUrl("file:///" + self.logic.getTempDirectoryBase(), qt.QUrl.TolerantMode))

  def onShowRegistrationParametersDatabaseFolder(self):
    qt.QDesktopServices().openUrl(qt.QUrl("file:///" + self.logic.registrationParameterFilesDir, qt.QUrl.TolerantMode))

  def onKeepTemporaryFilesToggled(self, toggle):
    self.logic.deleteTemporaryFiles = toggle

  def onApplyButton(self):
    if self.registrationInProgress:
      return self.abortRegistration()

    self.indicateRegistrationStart()
    try:
      self.logic.setCustomElastixBinDir(self.ui.customElastixBinDirSelector.currentPath)
      self.logic.deleteTemporaryFiles = not self.ui.keepTemporaryFilesCheckBox.checked
      self.logic.logStandardOutput = self.ui.showDetailedLogDuringExecutionCheckBox.checked

      self.logic.registerVolumesUsingParameterNode(self._parameterNode)

      # Apply computed transform to moving volume if output transform is computed to immediately see registration results
      movingVolumeNode = self.ui.movingVolumeSelector.currentNode()
      if self.ui.outputTransformSelector.currentNode() is not None \
          and movingVolumeNode is not None \
          and self.ui.outputVolumeSelector.currentNode() is None:
        movingVolumeNode.SetAndObserveTransformNodeID(self.ui.outputTransformSelector.currentNode().GetID())

    except Exception as e:
      print(e)
      self.addLog(f"Error: {e}")
      import traceback
      traceback.print_exc()
    finally:
      slicer.app.restoreOverrideCursor()
      self.registrationInProgress = False
      self.updateGUIFromParameterNode()

  def indicateRegistrationStart(self):
    self.registrationInProgress = True
    self.ui.applyButton.text = "Cancel"
    self.ui.statusLabel.plainText = ''
    slicer.app.setOverrideCursor(qt.Qt.WaitCursor)

  def abortRegistration(self):
    self.registrationInProgress = False
    self.logic.abortRequested = True
    self.ui.applyButton.text = "Cancelling..."
    self.ui.applyButton.enabled = False

  def addLog(self, text):
    self.ui.statusLabel.appendPlainText(text)
    slicer.app.processEvents()  # force update

  def onCustomElastixBinDirChanged(self, path):
    if os.path.exists(path):
      wasBlocked = self.ui.customElastixBinDirSelector.blockSignals(True)
      self.ui.customElastixBinDirSelector.addCurrentPathToHistory()
      self.ui.customElastixBinDirSelector.blockSignals(wasBlocked)
    self.logic.setCustomElastixBinDir(path)

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

  FIXED_VOLUME_REF = "FixedVolume"
  MOVING_VOLUME_REF = "MovingVolume"
  FIXED_VOLUME_MASK_REF = "FixedVolumeMask"
  MOVING_VOLUME_MASK_REF = "MovingVolumeMask"
  OUTPUT_VOLUME_REF = "OutputVolume"
  OUTPUT_TRANSFORM_REF = "OutputTransform"
  FORCE_GRID_TRANSFORM_PARAM = "ForceGridTransform"
  INITIAL_TRANSFORM_REF = "InitialTransform"
  REGISTRATION_PRESET_ID_PARAM = "RegistrationPresetId"

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

  def setDefaultParameters(self, parameterNode):
    """
    Initialize parameter node with default settings.
    """
    if not parameterNode.GetParameter(self.FORCE_GRID_TRANSFORM_PARAM):
      parameterNode.SetParameter(self.FORCE_GRID_TRANSFORM_PARAM, "False")
    if not parameterNode.GetParameter(self.REGISTRATION_PRESET_ID_PARAM):
      parameterNode.SetParameter(self.REGISTRATION_PRESET_ID_PARAM, "default0")

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
      os.path.join(self.scriptPath, '..'),
      os.path.join(self.scriptPath, '../../../bin'),
      # build tree
      os.path.join(self.scriptPath, '../../../../bin'),
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
      return settings.value(self.customElastixBinDirSettingsKey)
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
    elastixEnv["PATH"] = os.path.join(elastixBinDir, elastixEnv["PATH"]) if elastixEnv.get("PATH") else elastixBinDir

    import platform
    if platform.system() != 'Windows':
      elastixLibDir = os.path.abspath(os.path.join(elastixBinDir, '../lib'))
      elastixEnv["LD_LIBRARY_PATH"] = os.path.join(elastixLibDir, elastixEnv["LD_LIBRARY_PATH"]) if elastixEnv.get("LD_LIBRARY_PATH") else elastixLibDir

    return elastixEnv

  def getRegistrationPresets(self):
    if self.registrationPresets:
      return self.registrationPresets

    # Read database from XML file
    elastixParameterSetDatabasePath = os.path.join(self.scriptPath, 'Resources', 'RegistrationParameters', 'ElastixParameterSetDatabase.xml')
    if not os.path.isfile(elastixParameterSetDatabasePath):
      raise ValueError("Failed to open parameter set database: "+elastixParameterSetDatabasePath)
    elastixParameterSetDatabaseXml = vtk.vtkXMLUtilities.ReadElementFromFile(elastixParameterSetDatabasePath)

    # Create python list from XML for convenience
    self.registrationPresets = []
    for parameterSetIndex in range(elastixParameterSetDatabaseXml.GetNumberOfNestedElements()):
      parameterSetXml = elastixParameterSetDatabaseXml.GetNestedElement(parameterSetIndex)
      parameterFilesXml = parameterSetXml.FindNestedElementWithName('ParameterFiles')
      parameterFiles = []
      for parameterFileIndex in range(parameterFilesXml.GetNumberOfNestedElements()):
        parameterFiles.append(parameterFilesXml.GetNestedElement(parameterFileIndex).GetAttribute('Name'))
      self.registrationPresets.append([
        parameterSetXml.GetAttribute('id'),
        parameterSetXml.GetAttribute('modality'),
        parameterSetXml.GetAttribute('content'),
        parameterSetXml.GetAttribute('description'),
        parameterSetXml.GetAttribute('publications'),
        parameterFiles
      ])
    return self.registrationPresets

  def getRegistrationIndexByPresetId(self, presetId):
    for presetIndex, preset in enumerate(self.getRegistrationPresets()):
      if preset[RegistrationPresets_Id] == presetId:
        return presetIndex
    message = f"Registration preset with id '{presetId}' could not be found.  Falling back to default preset."
    logging.warning(message)
    self.addLog(message)
    return 0

  def getStartupInfo(self):
    import platform
    if platform.system() != 'Windows':
      return None

    # Hide console window (only needed on Windows)
    import subprocess
    info = subprocess.STARTUPINFO()
    info.dwFlags = 1
    info.wShowWindow = 0
    return info

  def startElastix(self, cmdLineArguments):
    self.addLog("Register volumes...")
    import subprocess
    executableFilePath = os.path.join(self.getElastixBinDir(),self.elastixFilename)
    logging.info("Register volumes using: "+executableFilePath+": "+repr(cmdLineArguments))
    if sys.platform == 'win32':
      return subprocess.Popen([executableFilePath] + cmdLineArguments, env=self.getElastixEnv(),
                            stdout=subprocess.PIPE, universal_newlines=True, startupinfo=self.getStartupInfo())
    else:
      return subprocess.Popen([executableFilePath] + cmdLineArguments, env=self.getElastixEnv(),
                            stdout=subprocess.PIPE, universal_newlines=True)

  def startTransformix(self, cmdLineArguments):
    self.addLog("Generate output...")
    import subprocess
    executableFilePath = os.path.join(self.getElastixBinDir(), self.transformixFilename)
    logging.info("Generate output using: " + executableFilePath + ": " + repr(cmdLineArguments))
    if sys.platform == 'win32':
      return subprocess.Popen([os.path.join(self.getElastixBinDir(), self.transformixFilename)] + cmdLineArguments,
                              env=self.getElastixEnv(),
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True,
                              startupinfo=self.getStartupInfo())
    else:
      return subprocess.Popen([os.path.join(self.getElastixBinDir(), self.transformixFilename)] + cmdLineArguments,
                              env=self.getElastixEnv(),
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)

  def logProcessOutput(self, process):
    # save process output (if not logged) so that it can be displayed in case of an error
    processOutput = ''
    import subprocess

    while True:
      try:
        stdout_line = process.stdout.readline()
        if not stdout_line:
          break
        stdout_line = stdout_line.rstrip()
        if self.logStandardOutput:
          self.addLog(stdout_line)
        else:
          processOutput += stdout_line + '\n'
      except UnicodeDecodeError as e:
        # Probably system locale is set to non-English, we cannot easily capture process output.
        # Code page conversion happens because `universal_newlines=True` sets process output to text mode.
        pass
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
    tempDir = qt.QDir(self.getTempDirectoryBase())
    tempDirName = qt.QDateTime().currentDateTime().toString("yyyyMMdd_hhmmss_zzz")
    fileInfo = qt.QFileInfo(qt.QDir(tempDir), tempDirName)
    dirPath = fileInfo.absoluteFilePath()
    qt.QDir().mkpath(dirPath)
    return dirPath

  def registerVolumesUsingParameterNode(self, parameterNode):
    presetId = parameterNode.GetParameter(self.REGISTRATION_PRESET_ID_PARAM)
    presetIdx = self.getRegistrationIndexByPresetId(presetId)
    registrationPreset = self.getRegistrationPresets()[presetIdx]
    parameterFilenames = registrationPreset[RegistrationPresets_ParameterFilenames]

    self.registerVolumes(
      fixedVolumeNode=parameterNode.GetNodeReference(self.FIXED_VOLUME_REF),
      movingVolumeNode=parameterNode.GetNodeReference(self.MOVING_VOLUME_REF),
      parameterFilenames=parameterFilenames,
      outputVolumeNode=parameterNode.GetNodeReference(self.OUTPUT_VOLUME_REF),
      outputTransformNode=parameterNode.GetNodeReference(self.OUTPUT_TRANSFORM_REF),
      fixedVolumeMaskNode=parameterNode.GetNodeReference(self.FIXED_VOLUME_MASK_REF),
      movingVolumeMaskNode=parameterNode.GetNodeReference(self.MOVING_VOLUME_MASK_REF),
      forceDisplacementFieldOutputTransform=slicer.util.toBool(parameterNode.GetParameter(self.FORCE_GRID_TRANSFORM_PARAM)),
      initialTransformNode=parameterNode.GetNodeReference(self.INITIAL_TRANSFORM_REF))

  def registerVolumes(self, fixedVolumeNode, movingVolumeNode, parameterFilenames=None, outputVolumeNode=None,
                      outputTransformNode=None, fixedVolumeMaskNode=None, movingVolumeMaskNode=None,
                      forceDisplacementFieldOutputTransform=True, initialTransformNode=None):

    self.abortRequested = False
    tempDir = self.createTempDirectory()
    self.addLog('Volume registration is started in working directory: '+tempDir)

    # Write inputs
    inputDir = os.path.join(tempDir, 'input')
    qt.QDir().mkpath(inputDir)

    inputParamsElastix = []

    # Add input volumes
    inputVolumes = [
      [fixedVolumeNode, 'fixed.mha', '-f'],
      [movingVolumeNode, 'moving.mha', '-m'],
      [fixedVolumeMaskNode, 'fixedMask.mha', '-fMask'],
      [movingVolumeMaskNode, 'movingMask.mha', '-mMask']
    ]

    for volumeNode, filename, paramName in inputVolumes:
      if not volumeNode:
        continue
      filePath = os.path.join(inputDir, filename)
      slicer.util.exportNode(volumeNode, filePath)
      inputParamsElastix.append(paramName)
      inputParamsElastix.append(filePath)

    # Add initial transform
    if initialTransformNode is not None:
      # Save node
      initialTransformFile = os.path.join(inputDir, 'initialTransform.h5')
      slicer.util.exportNode(initialTransformNode, initialTransformFile)
      # Save settings
      initialTransformParameterFile = os.path.join(inputDir, 'initialTransformParameter.txt')
      initialTransformSettings = [
        '(InitialTransformParametersFileName "NoInitialTransform")',
        '(HowToCombineTransforms "Compose")',
        '(Transform "File")',
        '(TransformFileName "%s")' % initialTransformFile,
        '\n'
      ]
      with open(initialTransformParameterFile, 'w') as f:
        f.write('\n'.join(initialTransformSettings))
      # Add parameters
      inputParamsElastix.append('-t0')
      inputParamsElastix.append(initialTransformParameterFile)

    # Specify output location
    resultTransformDir = os.path.join(tempDir, 'result-transform')
    qt.QDir().mkpath(resultTransformDir)
    inputParamsElastix += ['-out', resultTransformDir]

    # Specify parameter files
    if parameterFilenames is None:
      parameterFilenames = self.getRegistrationPresets()[0][RegistrationPresets_ParameterFilenames]
    for parameterFilename in parameterFilenames:
      inputParamsElastix.append('-p')
      parameterFilePath = os.path.abspath(os.path.join(self.registrationParameterFilesDir, parameterFilename))
      inputParamsElastix.append(parameterFilePath)

    # Run registration
    ep = self.startElastix(inputParamsElastix)
    self.logProcessOutput(ep)

    # Write results
    if not self.abortRequested:

      transformFileNameBase = os.path.join(resultTransformDir, 'TransformParameters.' + str(len(parameterFilenames)-1))

      #Load Linear Transform if available
      elastixTransformFileImported = False
      if outputTransformNode and (not forceDisplacementFieldOutputTransform):
        try:
          self.loadTransformFromFile(transformFileNameBase + '-Composite.h5', outputTransformNode)
          elastixTransformFileImported = True
        except:
          # Could not load transform (probably not linear and bspline)
          elastixTransformFileImported = False

      #Create temp results directory
      resultResampleDir = os.path.join(tempDir, 'result-resample')
      qt.QDir().mkpath(resultResampleDir)
      inputParamsTransformix = []
      inputParamsTransformix += ['-tp', transformFileNameBase + '.txt']
      inputParamsTransformix += ['-out', resultResampleDir]
      if outputVolumeNode:
        inputParamsTransformix += ['-in', os.path.join(inputDir, 'moving.mha')]

      if outputTransformNode:
        inputParamsTransformix += ['-def', 'all']

      #Run Transformix to get resampled moving volume or transformation as a displacement field
      if (outputVolumeNode is not None) or (not elastixTransformFileImported):
        tp = self.startTransformix(inputParamsTransformix)
        self.logProcessOutput(tp)

      if outputVolumeNode:
        #Load volume in Slicer
        outputVolumePath = os.path.join(resultResampleDir, "result.mhd")
        try:
          loadedOutputVolumeNode = slicer.util.loadVolume(outputVolumePath)
          outputVolumeNode.SetAndObserveImageData(loadedOutputVolumeNode.GetImageData())
          ijkToRas = vtk.vtkMatrix4x4()
          loadedOutputVolumeNode.GetIJKToRASMatrix(ijkToRas)
          outputVolumeNode.SetIJKToRASMatrix(ijkToRas)
          slicer.mrmlScene.RemoveNode(loadedOutputVolumeNode)
        except:
          self.addLog("Failed to load output volume from "+outputVolumePath)

      if outputTransformNode and (not elastixTransformFileImported):
        #Load transform in Slicer
        outputTransformPath = os.path.join(resultResampleDir, "deformationField.mhd")
        try:
          self.loadTransformFromFile(outputTransformPath, outputTransformNode)
        except:
          self.addLog("Failed to load output transform from "+outputTransformPath)
        if slicer.app.majorVersion >= 5 or (slicer.app.majorVersion >= 4 and slicer.app.minorVersion >= 11):
          outputTransformNode.AddNodeReferenceID(
            slicer.vtkMRMLTransformNode.GetMovingNodeReferenceRole(), movingVolumeNode.GetID()
          )
          outputTransformNode.AddNodeReferenceID(
            slicer.vtkMRMLTransformNode.GetFixedNodeReferenceRole(), fixedVolumeNode.GetID()
          )

    # Clean up
    if self.deleteTemporaryFiles:
      import shutil
      shutil.rmtree(tempDir)

    self.addLog("Registration is completed")

  def loadTransformFromFile(self, fileName, node):
    tmpNode = slicer.util.loadTransform(fileName)
    node.CopyContent(tmpNode)
    slicer.mrmlScene.RemoveNode(tmpNode)


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

    import SampleData
    sampleDataLogic = SampleData.SampleDataLogic()
    self.tumor1 = sampleDataLogic.downloadMRBrainTumor1()
    self.tumor2 = sampleDataLogic.downloadMRBrainTumor2()

    self.outputVolume = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode")
    self.outputVolume.CreateDefaultDisplayNodes()

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_Elastix_Explicit_Arguments()
    self.test_Elastix_ParameterNode()

  def test_Elastix_Explicit_Arguments(self):
    self.delayDisplay(f"Running test: test_Elastix_Explicit_Arguments", msec=500)

    logic = ElastixLogic()
    parameterFilenames = logic.getRegistrationPresets()[0][RegistrationPresets_ParameterFilenames]
    logic.registerVolumes(fixedVolumeNode=self.tumor1, movingVolumeNode=self.tumor2,
                          parameterFilenames=parameterFilenames, outputVolumeNode=self.outputVolume)

    self.delayDisplay('Test passed!')

  def test_Elastix_ParameterNode(self):
    self.delayDisplay(f"Running test: test_Elastix_ParameterNode", msec=500)

    logic = ElastixLogic()

    parameterNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScriptedModuleNode")
    parameterNode.SetNodeReferenceID(logic.FIXED_VOLUME_REF, self.tumor1.GetID())
    parameterNode.SetNodeReferenceID(logic.MOVING_VOLUME_REF, self.tumor2.GetID())
    parameterNode.SetNodeReferenceID(logic.OUTPUT_VOLUME_REF, self.outputVolume.GetID())
    parameterNode.SetParameter(logic.REGISTRATION_PRESET_ID_PARAM, "default0")

    logic.registerVolumesUsingParameterNode(parameterNode)

    self.delayDisplay('Test passed!')


RegistrationPresets_Id = 0
RegistrationPresets_Modality = 1
RegistrationPresets_Content = 2
RegistrationPresets_Description = 3
RegistrationPresets_Publications = 4
RegistrationPresets_ParameterFilenames = 5
