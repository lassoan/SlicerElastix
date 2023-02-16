from __future__ import print_function
import os
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
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
    self.parent.contributors = ["Andras Lasso (PerkLab - Queen's University)"]
    self.parent.helpText = """Align volumes based on image content using <a href="http://elastix.isi.uu.nl/">Elastix medical image registration toolbox</a>.
<p>Registration troubleshooting: check "Keep temporary files" option before starting regsitration and click on "Show temp folder" to open the folder that contains detailed logs.
<p>Edit registration parameters: open Advanced section, click "Show database folder", and edit presets. To add a new preset or modify registration phases, modify ElastixParameterSetDatabase.xml.
See <a href="http://elastix.bigr.nl/wiki/index.php/Parameter_file_database">registration parameter set database</a> and <a href="http://elastix.isi.uu.nl/doxygen/index.html">Elastix documentation</a> for more details."""
    #self.parent.helpText += self.getDefaultModuleDocumentationLink()
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
    maskingParametersCollapsibleButton = ctk.ctkCollapsibleButton()
    maskingParametersCollapsibleButton.text = "Masking"
    maskingParametersCollapsibleButton.collapsed = True
    self.layout.addWidget(maskingParametersCollapsibleButton)

    # Layout within the dummy collapsible button
    maskingParametersFormLayout = qt.QFormLayout(maskingParametersCollapsibleButton)

    #
    # fixed volume mask selector
    #
    self.fixedVolumeMaskSelector = slicer.qMRMLNodeComboBox()
    self.fixedVolumeMaskSelector.nodeTypes = ["vtkMRMLLabelMapVolumeNode"]
    self.fixedVolumeMaskSelector.addEnabled = False
    self.fixedVolumeMaskSelector.removeEnabled = False
    self.fixedVolumeMaskSelector.noneEnabled = True
    self.fixedVolumeMaskSelector.showHidden = False
    self.fixedVolumeMaskSelector.showChildNodeTypes = False
    self.fixedVolumeMaskSelector.setMRMLScene( slicer.mrmlScene )
    self.fixedVolumeMaskSelector.setToolTip("Areas of the fixed volume where mask label is 0 will be ignored in the registration.")
    maskingParametersFormLayout.addRow("Fixed volume mask: ", self.fixedVolumeMaskSelector)

    #
    # moving volume mask selector
    #
    self.movingVolumeMaskSelector = slicer.qMRMLNodeComboBox()
    self.movingVolumeMaskSelector.nodeTypes = ["vtkMRMLLabelMapVolumeNode"]
    self.movingVolumeMaskSelector.selectNodeUponCreation = True
    self.movingVolumeMaskSelector.addEnabled = False
    self.movingVolumeMaskSelector.removeEnabled = False
    self.movingVolumeMaskSelector.noneEnabled = True
    self.movingVolumeMaskSelector.showHidden = False
    self.movingVolumeMaskSelector.showChildNodeTypes = False
    self.movingVolumeMaskSelector.setMRMLScene( slicer.mrmlScene )
    self.movingVolumeMaskSelector.setToolTip("Areas of the moving volume where mask label is 0 will be ignored in the registration")
    maskingParametersFormLayout.addRow("Moving volume mask: ", self.movingVolumeMaskSelector)

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
    self.outputVolumeSelector.renameEnabled = True
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
    self.outputTransformSelector.renameEnabled = True
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

    self.forceDisplacementFieldOutputChecbox = qt.QCheckBox(" ")
    self.forceDisplacementFieldOutputChecbox.checked = False
    self.forceDisplacementFieldOutputChecbox.setToolTip("If this checkbox is checked then computed transform will be always returned as a grid transform (displacement field).")
    advancedFormLayout.addRow("Force grid output transform:", self.forceDisplacementFieldOutputChecbox)

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

    self.showRegistrationParametersDatabaseFolderButton = qt.QPushButton("Show database folder")
    self.showRegistrationParametersDatabaseFolderButton.toolTip = "Open the folder where temporary files are stored."
    self.showRegistrationParametersDatabaseFolderButton.setSizePolicy(qt.QSizePolicy.MinimumExpanding, qt.QSizePolicy.Preferred)
    advancedFormLayout.addRow("Registration presets:", self.showRegistrationParametersDatabaseFolderButton)

    customElastixBinDir = self.logic.getCustomElastixBinDir()
    self.customElastixBinDirSelector = ctk.ctkPathLineEdit()
    self.customElastixBinDirSelector.filters = ctk.ctkPathLineEdit.Dirs
    self.customElastixBinDirSelector.setCurrentPath(customElastixBinDir)
    self.customElastixBinDirSelector.setSizePolicy(qt.QSizePolicy.MinimumExpanding, qt.QSizePolicy.Preferred)
    self.customElastixBinDirSelector.setToolTip("Set bin directory of an Elastix installation (where elastix executable is located). "
      "If value is empty then default elastix (bundled with SlicerElastix extension) will be used.")
    advancedFormLayout.addRow("Custom Elastix toolbox location:", self.customElastixBinDirSelector)

    self.initialTransformSelector = slicer.qMRMLNodeComboBox()
    self.initialTransformSelector.nodeTypes = ["vtkMRMLTransformNode","vtkMRMLLinearTransformNode"]
    self.initialTransformSelector.addEnabled = False
    self.initialTransformSelector.renameEnabled = False
    self.initialTransformSelector.removeEnabled = True
    self.initialTransformSelector.noneEnabled = True
    self.initialTransformSelector.showHidden = False
    self.initialTransformSelector.showChildNodeTypes = False
    self.initialTransformSelector.setMRMLScene( slicer.mrmlScene )
    self.initialTransformSelector.setToolTip( "Start the registration from the selected initial transform." )
    advancedFormLayout.addRow("Initial transform: ", self.initialTransformSelector)

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
    self.showRegistrationParametersDatabaseFolderButton.connect('clicked(bool)', self.onShowRegistrationParametersDatabaseFolder)
    self.fixedVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)
    self.movingVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)
    self.outputVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)
    self.outputTransformSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)
    # Immediately update deleteTemporaryFiles in the logic to make it possible to decide to
    # keep the temporary file while the registration is running
    self.keepTemporaryFilesCheckBox.connect("toggled(bool)", self.onKeepTemporaryFilesToggled)

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

  def onShowRegistrationParametersDatabaseFolder(self):
    qt.QDesktopServices().openUrl(qt.QUrl("file:///" + self.logic.registrationParameterFilesDir, qt.QUrl.TolerantMode));

  def onKeepTemporaryFilesToggled(self, toggle):
    self.logic.deleteTemporaryFiles = toggle

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
      self.logic.setCustomElastixBinDir(self.customElastixBinDirSelector.currentPath)

      self.logic.deleteTemporaryFiles = not self.keepTemporaryFilesCheckBox.checked
      self.logic.logStandardOutput = self.showDetailedLogDuringExecutionCheckBox.checked

      parameterFilenames = self.logic.getRegistrationPresets()[self.registrationPresetSelector.currentIndex][RegistrationPresets_ParameterFilenames]

      self.logic.registerVolumes(self.fixedVolumeSelector.currentNode(), self.movingVolumeSelector.currentNode(),
        parameterFilenames = parameterFilenames,
        outputVolumeNode = self.outputVolumeSelector.currentNode(),
        outputTransformNode = self.outputTransformSelector.currentNode(),
        fixedVolumeMaskNode = self.fixedVolumeMaskSelector.currentNode(),
        movingVolumeMaskNode = self.movingVolumeMaskSelector.currentNode(),
        forceDisplacementFieldOutputTransform = self.forceDisplacementFieldOutputChecbox.checked,
        initialTransformNode = self.initialTransformSelector.currentNode())

      # Apply computed transform to moving volume if output transform is computed to immediately see registration results
      if ( (self.outputTransformSelector.currentNode() is not None)
          and (self.movingVolumeSelector.currentNode() is not None)
          and (self.outputVolumeSelector.currentNode() is None) ):
        self.movingVolumeSelector.currentNode().SetAndObserveTransformNodeID(self.outputTransformSelector.currentNode().GetID())

    except Exception as e:
      print(e)
      self.addLog("Error: {0}".format(e))
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
      return subprocess.Popen([os.path.join(self.getElastixBinDir(),self.transformixFilename)] + cmdLineArguments, env=self.getElastixEnv(),
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines = True, startupinfo=self.getStartupInfo())
    else:
      return subprocess.Popen([os.path.join(self.getElastixBinDir(),self.transformixFilename)] + cmdLineArguments, env=self.getElastixEnv(),
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines = True)

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
    import qt, slicer
    tempDir = qt.QDir(self.getTempDirectoryBase())
    tempDirName = qt.QDateTime().currentDateTime().toString("yyyyMMdd_hhmmss_zzz")
    fileInfo = qt.QFileInfo(qt.QDir(tempDir), tempDirName)
    dirPath = fileInfo.absoluteFilePath()
    qt.QDir().mkpath(dirPath)
    return dirPath

  def registerVolumes(self, fixedVolumeNode, movingVolumeNode, parameterFilenames = None, outputVolumeNode = None, outputTransformNode = None,
    fixedVolumeMaskNode = None, movingVolumeMaskNode = None, forceDisplacementFieldOutputTransform = True, initialTransformNode = None):

    self.abortRequested = False
    tempDir = self.createTempDirectory()
    self.addLog('Volume registration is started in working directory: '+tempDir)

    # Write inputs
    inputDir = os.path.join(tempDir, 'input')
    qt.QDir().mkpath(inputDir)

    inputParamsElastix = []

    # Add input volumes
    inputVolumes = []
    inputVolumes.append([fixedVolumeNode, 'fixed.mha', '-f'])
    inputVolumes.append([movingVolumeNode, 'moving.mha', '-m'])
    inputVolumes.append([fixedVolumeMaskNode, 'fixedMask.mha', '-fMask'])
    inputVolumes.append([movingVolumeMaskNode, 'movingMask.mha', '-mMask'])
    for [volumeNode, filename, paramName] in inputVolumes:
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
      initialTransformSettings = ['(InitialTransformParametersFileName "NoInitialTransform")',\
                                  '(HowToCombineTransforms "Compose")',\
                                  '(Transform "File")',\
                                  '(TransformFileName "%s")' % initialTransformFile,\
                                  '\n']
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
    if parameterFilenames == None:
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

      if (outputTransformNode) and (not elastixTransformFileImported):
        #Load transform in Slicer
        outputTransformPath = os.path.join(resultResampleDir, "deformationField.mhd")
        try:
          self.loadTransformFromFile(outputTransformPath, outputTransformNode)
        except:
          self.addLog("Failed to load output transform from "+outputTransformPath)
        if slicer.app.majorVersion >= 5 or (slicer.app.majorVersion >= 4 and slicer.app.minorVersion >= 11):
          outputTransformNode.AddNodeReferenceID(slicer.vtkMRMLTransformNode.GetMovingNodeReferenceRole(), movingVolumeNode.GetID())
          outputTransformNode.AddNodeReferenceID(slicer.vtkMRMLTransformNode.GetFixedNodeReferenceRole(), fixedVolumeNode.GetID())

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
    logic.registerVolumes(tumor1, tumor2, parameterFilenames = parameterFilenames, outputVolumeNode = outputVolume)

    self.delayDisplay('Test passed!')


RegistrationPresets_Id = 0
RegistrationPresets_Modality = 1
RegistrationPresets_Content = 2
RegistrationPresets_Description = 3
RegistrationPresets_Publications = 4
RegistrationPresets_ParameterFilenames = 5
