from __future__ import print_function
import os
import subprocess
import vtk, qt, slicer

from ElastixLib.utils import *
from ElastixLib.manager import PresetManagerLogic
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
import logging


#
# Elastix
#


class DatabaseNotFoundMessageBox(qt.QMessageBox):

  def __init__(self, text, *args):
    qt.QMessageBox.__init__(self, *args)
    self.standardButtons = qt.QMessageBox.RestoreDefaults

    self.file_path = None
    self.text = text

    self.addButton("Locate File", qt.QMessageBox.ActionRole)
    self.buttonClicked.connect(lambda button: self.handle_button_click(button))

  def handle_button_click(self, button):
    if self.buttonRole(button) == qt.QMessageBox.ActionRole:
      self.file_path = qt.QFileDialog.getOpenFileName(self, "Locate Elastix Database File", "", "XML files (*.xml)")


class Elastix(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "General Registration (Elastix)"
    self.parent.categories = ["Registration"]
    self.parent.associatedNodeTypes = ["vtkMRMLScriptedModuleNode"]
    self.parent.dependencies = []
    self.parent.contributors = ["Andras Lasso (PerkLab - Queen's University), Christian Herz (CHOP)"]
    self.parent.helpText = """Align volumes based on image content using <a href="https://elastix.dev">Elastix medical image registration toolbox</a>.
<p>Registration troubleshooting: check "Keep temporary files" option before starting regsitration and click on "Show temp folder" to open the folder that contains detailed logs.
<p>Edit registration parameters: open Advanced section, click "Show database folder", and edit presets. To add a new preset or modify registration phases, modify ElastixParameterSetDatabase.xml.
See <a href="http://elastix.bigr.nl/wiki/index.php/Parameter_file_database">registration parameter set database</a> and <a href="https://elastix.dev/doxygen/index.html">Elastix documentation</a> for more details."""
    self.parent.acknowledgementText = """
This module was originally developed by Andras Lasso (Queen's University, PerkLab)
to serve as a frontend to Elastix medical image registration toolbox.
If you use this module, please cite the following articles:
<ul><li>S. Klein, M. Staring, K. Murphy, M.A. Viergever, J.P.W. Pluim, "<a href="https://elastix.dev/marius/publications/2010_j_TMI.php">elastix: a toolbox for intensity based medical image registration</a>", IEEE Transactions on Medical Imaging, vol. 29, no. 1, pp. 196 - 205, January 2010.</li>
<li>D.P. Shamonin, E.E. Bron, B.P.F. Lelieveldt, M. Smits, S. Klein and M. Staring, "<a href="https://elastix.dev/marius/publications/2014_j_FNI.php">Fast Parallel Image Registration on CPU and GPU for Diagnostic Classification of Alzheimer's Disease</a>", Frontiers in Neuroinformatics, vol. 7, no. 50, pp. 1-15, January 2014.</li></ul>
See more information about Elastix medical image registration toolbox at <a href="https://elastix.dev">https://elastix.dev</a>.
"""
    slicer.app.connect("startupCompleted()", self.initializeElastixLib)

  def initializeElastixLib(self):
    import ElastixLib.ElastixPresetSubjectHierarchyPlugin as shp
    scriptedPlugin = slicer.qSlicerSubjectHierarchyScriptedPlugin(None)
    scriptedPlugin.setPythonSource(shp.ElastixPresetSubjectHierarchyPlugin.filePath)




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

  def setEditedNode(self, node, role='', context=''):
    self.setParameterNode(node)
    return node is not None

  def nodeEditable(self, node):
    return 0.7 if node is not None and node.GetAttribute('ModuleName') == self.moduleName else 0.0

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)

    self.logic = ElastixLogic()
    self.logic.logCallback = self.addLog
    self.registrationInProgress = False

    # Instantiate and connect widgets ...

    # Load widget from .ui file (created by Qt Designer).
    # Additional widgets can be instantiated manually and added to self.layout.
    uiWidget = slicer.util.loadUI(self.resourcePath('UI/Elastix.ui'))
    uiWidget.setMRMLScene(slicer.mrmlScene)

    self.layout.addWidget(uiWidget)
    self.ui = slicer.util.childWidgetVariables(uiWidget)

    self.ui.parameterNodeSelector.addAttribute("vtkMRMLScriptedModuleNode", "ModuleName", self.moduleName)
    self.ui.parameterNodeSelector.setNodeTypeLabel("ElastixParameters", "vtkMRMLScriptedModuleNode")

    self.refreshRegistrationPresetList()

    # These connections ensure that we update parameter node when scene is closed
    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)

    # connections
    self.ui.applyButton.connect('clicked(bool)', self.onApplyButton)
    self.ui.showTemporaryFilesFolderButton.connect('clicked(bool)', self.onShowTemporaryFilesFolder)
    self.ui.showBuiltinPresetFolderButton.connect('clicked(bool)', self.onShowBuiltinPresetsFolder)
    self.ui.showUserPresetFolderButton.connect('clicked(bool)', self.onShowUserPresetsFolder)
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
    self.ui.customElastixBinDirSelector.currentPathChanged.connect(self.onCustomElastixBinDirChanged)

    # Immediately update deleteTemporaryFiles in the logic to make it possible to decide to
    # keep the temporary file while the registration is running
    self.ui.keepTemporaryFilesCheckBox.connect("toggled(bool)", self.onKeepTemporaryFilesToggled)
    self.ui.managePresetsButton.connect("clicked()", self.onPresetManagerClicked)

    self.initializeParameterNode()

  def onReload(self):

    with slicer.util.tryWithErrorDisplay("Failed to reload the module."):

      packageName='ElastixLib'
      submoduleNames=['preset', 'utils', 'database', 'manager', 'ElastixPresetSubjectHierarchyPlugin']
      import importlib
      package = importlib.import_module(packageName)
      for submoduleName in submoduleNames:
        importlib.import_module(f"{packageName}.{submoduleName}")

      ScriptedLoadableModuleWidget.onReload(self)

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
    self.refreshRegistrationPresetList()

  def initializeParameterNode(self):
    self.setParameterNode(self.logic.getParameterNode() if not self._parameterNode else self._parameterNode)

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
    self._parameterNode.SetParameter(self.logic.REGISTRATION_PRESET_ID_PARAM, registrationPreset.getID())

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

    self.ui.fixedVolumeSelector.setCurrentNode(self._parameterNode.GetNodeReference(self.logic.FIXED_VOLUME_REF))
    self.ui.movingVolumeSelector.setCurrentNode(self._parameterNode.GetNodeReference(self.logic.MOVING_VOLUME_REF))
    self.ui.fixedVolumeMaskSelector.setCurrentNode(self._parameterNode.GetNodeReference(self.logic.FIXED_VOLUME_MASK_REF))
    self.ui.movingVolumeMaskSelector.setCurrentNode(self._parameterNode.GetNodeReference(self.logic.MOVING_VOLUME_MASK_REF))
    self.ui.initialTransformSelector.setCurrentNode(self._parameterNode.GetNodeReference(self.logic.INITIAL_TRANSFORM_REF))

    self.ui.outputVolumeSelector.setCurrentNode(self._parameterNode.GetNodeReference(self.logic.OUTPUT_VOLUME_REF))
    self.ui.outputTransformSelector.setCurrentNode(self._parameterNode.GetNodeReference(self.logic.OUTPUT_TRANSFORM_REF))

    self.ui.forceDisplacementFieldOutputCheckbox.checked = \
      slicer.util.toBool(self._parameterNode.GetParameter(self.logic.FORCE_GRID_TRANSFORM_PARAM))

    registrationPresetIndex = \
      self.logic.getIdxByPresetId(self._parameterNode.GetParameter(self.logic.REGISTRATION_PRESET_ID_PARAM))
    self.ui.registrationPresetSelector.setCurrentIndex(registrationPresetIndex)

    self.updateApplyButtonState()

    # All the GUI updates are done
    self._updatingGUIFromParameterNode = False

  def onPresetManagerClicked(self):
    from ElastixLib.manager import PresetManagerDialog
    manager = self.logic
    dialog = PresetManagerDialog(manager)
    dialog.exec_(self._parameterNode.GetParameter(self.logic.REGISTRATION_PRESET_ID_PARAM))
    self.refreshRegistrationPresetList()
    preset = dialog.getSelectedPreset()
    idx = self.logic.getIdxByPresetId(preset.getID())
    self.ui.registrationPresetSelector.currentIndex = idx

  def onShowTemporaryFilesFolder(self):
    showFolder(getTempDirectoryBase())

  def onShowBuiltinPresetsFolder(self):
    showFolder(self.logic.getBuiltinPresetsDir())

  def onShowUserPresetsFolder(self):
    showFolder(self.logic.getUserPresetsDir())

  def onKeepTemporaryFilesToggled(self, toggle):
    self.logic.deleteTemporaryFiles = toggle

  def onApplyButton(self):
    if self.registrationInProgress:
      self.logic.cancelRequested = True
      self.registrationInProgress = False
    else:
      with slicer.util.tryWithErrorDisplay("Failed to compute results.", waitCursor=True):
        self.ui.statusLabel.plainText = ''
        try:
          self.registrationInProgress = True
          self.updateApplyButtonState()

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
        finally:
          self.registrationInProgress = False
    self.updateApplyButtonState()

  def updateApplyButtonState(self):
    if self.registrationInProgress or self.logic.isRunning:
      if self.logic.cancelRequested:
        self.ui.applyButton.text = "Cancelling..."
        self.ui.applyButton.enabled = False
      else:
        self.ui.applyButton.text = "Cancel"
        self.ui.applyButton.enabled = True
    else:
      fixedVolumeNode = self._parameterNode.GetNodeReference(self.logic.FIXED_VOLUME_REF)
      movingVolumeNode = self._parameterNode.GetNodeReference(self.logic.MOVING_VOLUME_REF)
      outputVolumeNode = self._parameterNode.GetNodeReference(self.logic.OUTPUT_VOLUME_REF)
      outputTransformNode = self._parameterNode.GetNodeReference(self.logic.OUTPUT_TRANSFORM_REF)
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

  def addLog(self, text):
    self.ui.statusLabel.appendPlainText(text)
    slicer.app.processEvents()  # force update

  def onCustomElastixBinDirChanged(self, path):
    if os.path.exists(path):
      wasBlocked = self.ui.customElastixBinDirSelector.blockSignals(True)
      self.ui.customElastixBinDirSelector.addCurrentPathToHistory()
      self.ui.customElastixBinDirSelector.blockSignals(wasBlocked)
    self.logic.setCustomElastixBinDir(path)

  def refreshRegistrationPresetList(self):
    wasBlocked = self.ui.registrationPresetSelector.blockSignals(True)
    self.ui.registrationPresetSelector.clear()
    for preset in self.logic.getRegistrationPresets(force_refresh=True):
      self.ui.registrationPresetSelector.addItem(preset.getName())
    self.ui.registrationPresetSelector.blockSignals(wasBlocked)


#
# ElastixLogic
#

class ElastixLogic(ScriptedLoadableModuleLogic, PresetManagerLogic):
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

  DEFAULT_PRESET_ID = "default0"

  INPUT_DIR_NAME = "input"
  OUTPUT_RESAMPLE_DIR_NAME = "result-resample"
  OUTPUT_TRANSFORM_DIR_NAME = "result-transform"

  def __init__(self):
    ScriptedLoadableModuleLogic.__init__(self)
    PresetManagerLogic.__init__(self)

    self.isRunning = False
    self.cancelRequested = False
    self.deleteTemporaryFiles = True
    self.logStandardOutput = False
    self.customElastixBinDirSettingsKey = 'Elastix/CustomElastixPath'

    self.scriptPath = os.path.dirname(os.path.abspath(__file__))
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
      parameterNode.SetParameter(self.REGISTRATION_PRESET_ID_PARAM, self.DEFAULT_PRESET_ID)

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
    return slicer.util.settingsValue(self.customElastixBinDirSettingsKey, '')

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

  def startElastix(self, cmdLineArguments):
    self.addLog("Register volumes...")
    executableFilePath = os.path.join(self.getElastixBinDir(), self.elastixFilename)
    logging.info(f"Register volumes using: {executableFilePath}: {cmdLineArguments!r}")
    return self._createSubProcess(executableFilePath, cmdLineArguments)

  def startTransformix(self, cmdLineArguments):
    self.addLog("Generate output...")
    executableFilePath = os.path.join(self.getElastixBinDir(), self.transformixFilename)
    logging.info(f"Generate output using: {executableFilePath}: {cmdLineArguments!r}")
    return self._createSubProcess(executableFilePath, cmdLineArguments)

  def _createSubProcess(self, executableFilePath, cmdLineArguments):
    return subprocess.Popen([executableFilePath] + cmdLineArguments, env=self.getElastixEnv(),
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True,
                            startupinfo=self.getStartupInfo())

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
      if self.cancelRequested:
        process.kill()
        break

    process.stdout.close()
    return_code = process.wait()
    if return_code and not self.cancelRequested:
      if processOutput:
        self.addLog(processOutput)
      raise subprocess.CalledProcessError(return_code, "elastix")

  def registerVolumesUsingParameterNode(self, parameterNode):
    presetId = parameterNode.GetParameter(self.REGISTRATION_PRESET_ID_PARAM)
    registrationPreset = self.getPresetByID(presetId)
    parameterFilenames = registrationPreset.getParameterFiles()

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

    self.isRunning = True
    tempDir = createTempDirectory()

    try:
      if parameterFilenames is None:
        self.addLog(f"Using default registration preset with id '{self.DEFAULT_PRESET_ID}'")
        defaultPreset = self.getPresetByID(self.DEFAULT_PRESET_ID)
        parameterFilenames = defaultPreset.getParameterFiles()

      self.cancelRequested = False

      self.addLog(f'Volume registration is started in working directory: {tempDir}')

      # Specify (and create) input/output locations
      inputDir = createDirectory(os.path.join(tempDir, self.INPUT_DIR_NAME))
      resultTransformDir = createDirectory(os.path.join(tempDir, self.OUTPUT_TRANSFORM_DIR_NAME))

      # compose parameters for running Elastix
      inputParamsElastix = self._addInputVolumes(inputDir, [
        [fixedVolumeNode, 'fixed.mha', '-f'],
        [movingVolumeNode, 'moving.mha', '-m'],
        [fixedVolumeMaskNode, 'fixedMask.mha', '-fMask'],
        [movingVolumeMaskNode, 'movingMask.mha', '-mMask']
      ])

      if initialTransformNode is not None:
        inputParamsElastix += self._addInitialTransform(initialTransformNode, inputDir)

      inputParamsElastix += self._addParameterFiles(parameterFilenames)
      inputParamsElastix += ['-out', resultTransformDir]

      elastixProcess = self.startElastix(inputParamsElastix)
      self.logProcessOutput(elastixProcess)

      if self.cancelRequested:
        self.addLog("User requested cancel.")
      else:
        self._processElastixOutput(tempDir, parameterFilenames, fixedVolumeNode, movingVolumeNode,
                                   outputVolumeNode, outputTransformNode, forceDisplacementFieldOutputTransform)
        self.addLog("Registration is completed")

    finally: # Clean up
      if self.deleteTemporaryFiles:
        import shutil
        shutil.rmtree(tempDir)
      self.isRunning = False
      self.cancelRequested = False

  def _processElastixOutput(self, tempDir, parameterFilenames, fixedVolumeNode, movingVolumeNode, outputVolumeNode,
                            outputTransformNode, forceDisplacementFieldOutputTransform):

    resultTransformDir = os.path.join(tempDir, self.OUTPUT_TRANSFORM_DIR_NAME)
    transformFileNameBase = os.path.join(resultTransformDir, 'TransformParameters.' + str(len(parameterFilenames) - 1))

    # Load Linear Transform if available
    elastixTransformFileImported = False
    if outputTransformNode is not None and not forceDisplacementFieldOutputTransform:
      # NB: if return value is False, Could not load transform (probably not linear and bspline)
      try:
        self.loadTransformFromFile(f"{transformFileNameBase}-Composite.h5", outputTransformNode)
        elastixTransformFileImported = True
      except:
        elastixTransformFileImported = False

    resultResampleDir = createDirectory(os.path.join(tempDir, self.OUTPUT_RESAMPLE_DIR_NAME))
    # Run Transformix to get resampled moving volume or transformation as a displacement field
    if outputVolumeNode is not None or not elastixTransformFileImported:
      inputParamsTransformix = [
        '-tp', f'{transformFileNameBase}.txt',
        '-out', resultResampleDir
      ]
      if outputVolumeNode:
        inputDir = os.path.join(tempDir, self.INPUT_DIR_NAME)
        inputParamsTransformix += ['-in', os.path.join(inputDir, 'moving.mha')]

      if outputTransformNode:
        inputParamsTransformix += ['-def', 'all']

      transformixProcess = self.startTransformix(inputParamsTransformix)
      self.logProcessOutput(transformixProcess)

    if outputVolumeNode:
      self._loadTransformedOutputVolume(outputVolumeNode, resultResampleDir)

    if outputTransformNode is not None and not elastixTransformFileImported:
      outputTransformPath = os.path.join(resultResampleDir, "deformationField.mhd")
      try:
        self.loadTransformFromFile(outputTransformPath, outputTransformNode)
      except:
        raise RuntimeError(f"Failed to load output transform from {outputTransformPath}")

      if slicer.app.majorVersion >= 5 or (slicer.app.majorVersion >= 4 and slicer.app.minorVersion >= 11):
        outputTransformNode.AddNodeReferenceID(
          slicer.vtkMRMLTransformNode.GetMovingNodeReferenceRole(), movingVolumeNode.GetID()
        )
        outputTransformNode.AddNodeReferenceID(
          slicer.vtkMRMLTransformNode.GetFixedNodeReferenceRole(), fixedVolumeNode.GetID()
        )

  def _loadTransformedOutputVolume(self, outputVolumeNode, resultResampleDir):
    outputVolumePath = os.path.join(resultResampleDir, "result.mhd")
    try:
      loadedOutputVolumeNode = slicer.util.loadVolume(outputVolumePath)
      outputVolumeNode.SetAndObserveImageData(loadedOutputVolumeNode.GetImageData())
      ijkToRas = vtk.vtkMatrix4x4()
      loadedOutputVolumeNode.GetIJKToRASMatrix(ijkToRas)
      outputVolumeNode.SetIJKToRASMatrix(ijkToRas)
      slicer.mrmlScene.RemoveNode(loadedOutputVolumeNode)
    except:
      raise RuntimeError(f"Failed to load output volume from {outputVolumePath}")

  def _addInputVolumes(self, inputDir, inputVolumes):
    params = []
    for volumeNode, filename, paramName in inputVolumes:
      if not volumeNode:
        continue
      filePath = os.path.join(inputDir, filename)
      slicer.util.exportNode(volumeNode, filePath)
      params += [paramName, filePath]
    return params

  def _addParameterFiles(self, parameterFilenames):
    params = []
    for parameterFilename in parameterFilenames:
      parameterFilePath = os.path.abspath(parameterFilename)
      params += ['-p', parameterFilePath]
    return params

  def _addInitialTransform(self, initialTransformNode, inputDir):
    # Save node
    initialTransformFile = os.path.join(inputDir, 'initialTransform.h5')
    slicer.util.exportNode(initialTransformNode, initialTransformFile)
    # Compose settings
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

    return ['-t0', initialTransformParameterFile]

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
    self.test_ElastixPresets()
    self.test_CopyAndDeleteElastixPreset()
    self.test_Elastix_Default_Registration_Preset()
    self.test_Elastix_Explicit_Arguments()
    self.test_Elastix_ParameterNode()

  def test_Elastix_Default_Registration_Preset(self):
    self.delayDisplay(f"Running test: test_Elastix_Default_Registration_Preset", msec=500)
    logic = ElastixLogic()
    logic.registerVolumes(fixedVolumeNode=self.tumor1, movingVolumeNode=self.tumor2, outputVolumeNode=self.outputVolume)
    self.delayDisplay('Test passed!')

  def test_Elastix_Explicit_Arguments(self):
    self.delayDisplay(f"Running test: test_Elastix_Explicit_Arguments", msec=500)

    logic = ElastixLogic()
    parameterFilenames = logic.getRegistrationPresets()[0].getParameterFiles()
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

  def test_ElastixPresets(self):
    self.delayDisplay(f"Running test: test_ElastixPresets", msec=500)

    from ElastixLib.preset import Preset, InScenePreset, createPreset

    createPreset("test123", "CT", "foo", "bar", "None")

    # create in scene preset from scratch and delete to make sure that nodes were removed
    preset = InScenePreset()
    node = preset.getPresetNode()
    self.assertIsNotNone(node)
    preset.delete()
    self.assertIsNone(node.GetScene())

    self.delayDisplay('Test passed!')


  def test_CopyAndDeleteElastixPreset(self):
    self.delayDisplay(f"Running test: test_CopyAndDeleteElastixPreset", msec=500)

    from ElastixLib.database import BuiltinElastixDatabase
    db = BuiltinElastixDatabase()
    presets = db.getRegistrationPresets()
    self.assertTrue(len(presets) > 0)

    from ElastixLib.preset import copyPreset
    preset = copyPreset(presets[0])

    preset.delete()

    self.delayDisplay('Test passed!')
