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
    self.forceDisplacementFieldOutputChecbox.checked = True
    self.forceDisplacementFieldOutputChecbox.setToolTip("If this checkbox is checked then computed transform will be always returned as a grid transform (displacement field). This may result in more accurate reproduction of the original Elastix transform but requires magnitudes more storage space.")
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
        forceDisplacementFieldOutputTransform = self.forceDisplacementFieldOutputChecbox.checked)

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

  def getElastixInitialTransform(self, fileContents):
    # Find and parse '(InitialTransformParametersFileName "C:\Users\andra\AppData\Local\Temp\Slicer\Elastix\20190808_122649_419\result-transform\TransformParameters.0.txt")'
    # return None if no initial transform is specified.
    initialTransformFilename = self.getElastixParameters(fileContents, "InitialTransformParametersFileName")[0]
    if initialTransformFilename == "NoInitialTransform":
      return None
    else:
      return initialTransformFilename

  def getElastixParameters(self, fileContents, fieldName, type="text"):
    parameterLine = next(s for s in fileContents if "("+fieldName+" " in s)
    if type == "text":
        import shlex # use shlex split (instead of regular split) to preserve spaces in quoted string
        parameters = shlex.split(parameterLine.strip("()"))
        parameters.pop(0) # remove fieldName
    else:
        parameters = parameterLine.strip("()").split(" ")
        parameters.pop(0) # remove fieldName
        if type == "float":
            parameters = [ float(x) for x in parameters ]
        elif type == "int":
            parameters = [ int(x) for x in parameters ]
    return parameters

  def readElastixTransformToVTK(self, filename, outputGeneralTransform):
    """
    Append transform stored in filename (and recursively, initial transform
    referenced in that transform file) to outputGeneralTransform
    """
    if self.readElastixLinearTransformToVTK(filename, outputGeneralTransform):
      return True
    elif self.readElastixBsplineTransformToVTK(filename, outputGeneralTransform):
      return True
    logging.warning("Cannot interpret transform file: {0}".format(filename))
    return False

  def readElastixLinearTransformToVTK(self, filename, outputGeneralTransform):
    """
    Example transform file that this method can parse:

(Transform "EulerTransform")
(NumberOfParameters 6)
(TransformParameters 0.022507 0.013835 0.013726 7.760838 4.879223 -0.014589)
(InitialTransformParametersFileName "NoInitialTransform")
(UseBinaryFormatForTransformationParameters "false")
(HowToCombineTransforms "Compose")
...
// EulerTransform specific
(CenterOfRotationPoint 0.0002500000 0.0002500000 0.0000000000)
(ComputeZYX "false")

    """
    f = open(filename, 'r')
    fileContents = f.read()
    f.close()
    fileContents = fileContents.split("\n")

    # Find and parse '(Transform "EulerTransform")'
    transformType = self.getElastixParameters(fileContents, "Transform")[0]
    supportedTransformTypes = ["EulerTransform", "TranslationTransform"]
    if transformType not in supportedTransformTypes:
      return False

    import numpy as np
    from math import sin, cos

    # Find and parse '(TransformParameters 0.022507 0.013835 0.013726 7.760838 4.879223 -0.014589)'
    transformParams = self.getElastixParameters(fileContents, "TransformParameters", type="float")

    if transformType == "EulerTransform":
        [rx,ry,rz]=transformParams[0:3]
        [tx,ty,tz]=transformParams[3:6]
        # Find and parse '(ComputeZYX "false")'
        computeZYX = (self.getElastixParameters(fileContents, "ComputeZYX") == "true")
        #Parse center of rotation point
        centerOfRotation = self.getElastixParameters(fileContents, "CenterOfRotationPoint", type="float")
    elif transformType == "TranslationTransform":
        [rx,ry,rz] = [0, 0, 0]
        [tx,ty,tz]=transformParams[0:3]
        computeZYX = None

    rotX = np.array([[1.0, 0.0, 0.0], [0.0, cos(rx), -sin(rx)], [0.0, sin(rx), cos(rx)]])
    rotY = np.array([[cos(ry), 0.0, sin(ry)], [0.0, 1.0, 0.0], [-sin(ry), 0.0, cos(ry)]])
    rotZ = np.array([[cos(rz), -sin(rz), 0.0], [sin(rz), cos(rz), 0.0], [0.0, 0.0, 1.0]])

    if computeZYX:
        # Aply the rotation first around Y then X then Z
        fixedToMovingDirection = np.dot(np.dot(rotZ, rotY), rotX)
    else:
        # Like VTK transformation order
        fixedToMovingDirection = np.dot(np.dot(rotZ, rotX), rotY)

    fixedToMoving = np.eye(4)
    fixedToMoving[0:3,0:3] = fixedToMovingDirection
    if transformType == "EulerTransform":
        offset = np.array([tx,ty,tz]) + np.array(centerOfRotation)
        offset[0] -= np.dot(fixedToMovingDirection[0,:], np.array(centerOfRotation))
        offset[1] -= np.dot(fixedToMovingDirection[1,:], np.array(centerOfRotation))
        offset[2] -= np.dot(fixedToMovingDirection[2,:], np.array(centerOfRotation))
        fixedToMoving[0:3,3] = offset
    else:
        fixedToMoving[0:3,3] = [tx, ty, tz]

    # Create Slicer linear transform ("to parent" direction, in RAS)
    ras2lps = np.array([[-1,0,0,0],[0,-1,0,0],[0,0,1,0],[0,0,0,1]])
    #movingToFixed = np.dot(np.dot(ras2lps, np.linalg.inv(fixedToMoving)), ras2lps)
    fixedToMoving = np.dot(np.dot(ras2lps, fixedToMoving), ras2lps)

    linearTransform = vtk.vtkTransform()
    #linearTransform.SetMatrix(slicer.util.vtkMatrixFromArray(fixedToMoving))
    linearTransform.SetMatrix(vtkMatrixFromArray(fixedToMoving))
    outputGeneralTransform.Concatenate(linearTransform)

    # Apply initial transform
    initialTransformFilename = self.getElastixInitialTransform(fileContents)
    if initialTransformFilename:
      return self.readElastixTransformToVTK(initialTransformFilename, outputGeneralTransform)
    else:
      return True

  def readElastixBsplineTransformToVTK(self, filename, outputGeneralTransform):
    """
    Example transform file that this method can parse:

(Transform "BSplineTransform")
(NumberOfParameters 14079)
(TransformParameters -1.582768 -2.176280 -2.277018 -2.337208 -2.354932 -2.369041 -2.385792 -2.454384 -2.621675 -2.933880 -3.437024 -4.059322 -4.728611 -5.334967 -5.763369 -6.043695 -6.134818 -6.037127 -4.762045 -2.565570 -3.332468 -3.369060 -3.275388 -3.052726 -2.799502 -2.574235 -2.456526 -2.522779 -2.853316 -3.524713 -4.421547 -5.427602 -6.377478 -7.100459 -7.626606 -7.897451 -7.879966 -6.324409 -2.931989 -3.748148 -3.760435 -3.595327 -3.232598 -2.811981 -2.438792 -2.205577 -2.202351 -2.513089 -3.209363 -4.168939 -5.222673 -6.230759 -7.044831 -7.680061 -8.059975 -8.114408 -6.587659 -3.364812 -4.231531 -4.195471 -3.899327 -3.285260 -2.617496 -2.120290 -1.842357 -1.870998 -2.157868 -2.828671 -3.807870 -4.820734 -5.820099 -6.723304 -7.493268 -8.007571 -8.155525 -6.724372 -3.817164 -4.730721 -4.605695 -4.089828 -3.078856 -2.084440 -1.598435 -1.496621 -1.724399 -2.167666 -2.791375 -3.563138 -4.346004 -5.231881 -6.204638 -7.121226 -7.761551 -7.999510 -6.711416 -4.302311 -5.317471 -5.144386 -4.478694 -3.183927 -1.906235 -1.397005 -1.412809 -1.775975 -2.296228 -2.749983 -3.285681 -3.936267 -4.714865 -5.674729 -6.670518 -7.403329 -7.722524 -6.604398 -4.781134 -6.001780 -5.907385 -5.339411 -4.142015 -2.819819 -2.116275 -1.938445 -2.092988 -2.371285 -2.583278 -2.961964 -3.731162 -4.538286 -5.252899 -6.163010 -6.916800 -7.298861 -6.373077 -5.199465 -6.651616 -6.690257 -6.307974 -5.339619 -4.167560 -3.289714 -2.700487 -2.367756 -2.330891 -2.438468 -2.670840 -3.256285 -4.023645 -4.706516 -5.534694 -6.327845 -6.803700 -6.085845 -5.499376 -7.130511 -7.285346 -7.025110 -6.144675 -5.033974 -3.987640 -3.224244 -2.679698 -2.262020 -2.195104 -2.327927 -2.485439 -2.906834 -3.798234 -4.701975 -5.654010 -6.304904 -5.804929 -5.611640 -7.287873 -7.476546 -7.223271 -6.279586 -5.123278 -4.113464 -3.318564 -2.701933 -2.194391 -2.061826 -2.119997 -2.240663 -2.466581 -3.136332 -4.072320 -5.142424 -5.919172 -5.558873 -5.466741 -6.972768 -7.047167 -6.632689 -5.487979 -4.187485 -3.283773 -2.647300 -2.342715 -2.220498 -2.277389 -2.362278 -2.503152 -2.727722 -3.241819 -4.063286 -5.040453 -5.762653 -5.375759 -5.131854 -6.349517 -6.244660 -5.620919 -4.309470 -2.965940 -2.138186 -1.814305 -1.983815 -2.231432 -2.439861 -2.651611 -2.951627 -3.337460 -3.822805 -4.450679 -5.218710 -5.769706 -5.242077 -4.673864 -5.582119 -5.316501 -4.561341 -3.253361 -2.007859 -1.380649 -1.314547 -1.648623 -2.076266 -2.334231 -2.624553 -3.236088 -3.906782 -4.475520 -5.004057 -5.547004 -5.874257 -5.143959 -4.154413 -4.815857 -4.464122 -3.696772 -2.548121 -1.537219 -1.129328 -1.182572 -1.570646 -1.987858 -2.234973 -2.527437 -3.372160 -4.365728 -5.021775 -5.503827 -5.857734 -5.984946 -5.054489 -3.631364 -4.191796 -3.884969 -3.264469 -2.406477 -1.681310 -1.428742 -1.532484 -1.888538 -2.274829 -2.529131 -2.870001 -3.710072 -4.652622 -5.287556 -5.725415 -5.977893 -6.004890 -4.942209 -3.143677 -3.694660 -3.498864 -3.092950 -2.557368 -2.125169 -1.996948 -2.122646 -2.456483 -2.841416 -3.115018 -3.487133 -4.167648 -4.899033 -5.429845 -5.803174 -5.992876 -5.970230 -4.818297 -2.677716 -3.250427 -3.172247 -2.966231 -2.696601 -2.515752 -2.542844 -2.746957 -3.095556 -3.483088 -3.803410 -4.161994 -4.662828 -5.170202 -5.542121 -5.804167 -5.912107 -5.840230 -4.630725 -2.288585 -2.879167 -2.892949 -2.834323 -2.745954 -2.738350 -2.888778 -3.164037 -3.528835 -3.918785 -4.269247 -4.608634 -4.965046 -5.287598 -5.520160 -5.680982 -5.719837 -5.612731 -4.392351 -1.298798 -1.782697 -1.906377 -2.035387 -2.169659 -2.347753 -2.581976 -2.854069 -3.143892 -3.428342 -3.684162 -3.905831 -4.087539 -4.226968 -4.317911 -4.369968 -4.338602 -4.214824 -3.235677 -2.294553 -3.095789 -3.193169 -3.196297 -3.097282 -2.965734 -2.827116 -2.779854 -2.919205 -3.300626 -3.979329 -4.861654 -5.853438 -6.770963 -7.423832 -7.859073 -8.030825 -7.934240 -6.270933 -3.599955 -4.611913 -4.631818 -4.419823 -3.891688 -3.213281 -2.577858 -2.158015 -2.107663 -2.529315 -3.529374 -4.869862 -6.415066 -7.902770 -9.050346 -9.916280 -10.420624 -10.477101 -8.447090 -4.037602 -5.098372 -5.124823 -4.966558 -4.207496 -3.035168 -2.025836 -1.280842 -0.985521 -1.338613 -2.272950 -4.097105 -5.885256 -7.510847 -8.761902 -9.827044 -10.657937 -10.835847 -8.851432 -4.539369 -5.607338 -5.554360 -5.234398 -3.938910 -2.217514 -0.988994 0.056202 -0.152310 -0.514181 -0.080107 -2.733898 -4.972935 -6.572304 -8.029103 -9.414322 -10.601959 -10.933696 -9.091946 -5.062468 -6.056546 -5.728629 -4.832666 -2.590131 -0.192412 0.286860 0.587254 1.083788 0.367911 -0.736753 -2.217506 -3.775349 -5.041329 -6.858822 -8.778533 -10.261258 -10.739961 -9.115389 -5.619746 -6.621575 -6.087711 -4.719974 -1.717556 2.132797 1.529664 1.207660 1.023492 0.323121 -0.173578 -1.363633 -2.256367 -2.722301 -5.627957 -8.030261 -9.711990 -10.333826 -8.980081 -6.154069 -7.396559 -7.007696 -5.895583 -2.941806 2.937343 3.074326 1.534304 -0.187431 -0.047983 0.443418 -0.727106 -3.275733 -5.350629 -5.310525 -7.245307 -8.904110 -9.654195 -8.625071 -6.612981 -8.195585 -8.115996 -7.447268 -5.218757 -0.978191 -0.003584 0.570824 0.697709 0.271669 -0.505971 -1.091563 -2.282474 -5.186139 -4.655093 -6.187034 -7.817277 -8.808739 -8.171817 -6.938999 -8.826895 -9.051150 -8.587662 -6.743563 -4.448960 -0.468561 -0.304888 -1.782144 0.068141 0.677965 -0.985588 1.178904 2.797702 -2.144419 -4.463358 -6.406290 -7.895057 -7.733213 -7.050893 -9.075585 -9.470191 -9.022433 -6.767301 -3.619622 -0.665859 -1.332498 -1.869366 -0.196030 0.986984 0.498600 -1.065128 1.200596 -0.458150 -3.013205 -5.263988 -7.162394 -7.352426 -6.867050 -8.726303 -9.025078 -8.439198 -6.087515 -2.374402 -0.935590 0.171932 0.499073 -0.402584 -1.344634 -0.496797 -1.351165 0.383073 0.447871 -2.878529 -4.993191 -6.859234 -7.071975 -6.463899 -7.977640 -8.017758 -7.125840 -4.749282 -2.384365 0.246202 1.243738 -0.278539 -0.705850 -1.249976 -1.756716 -1.131593 -1.601264 -2.031407 -3.727436 -5.368853 -6.887129 -6.875958 -5.917496 -7.027758 -6.765307 -5.662694 -2.954354 -0.058197 1.346869 0.276948 -0.374729 -0.500850 -1.100060 -1.810466 -2.348607 -2.829475 -4.100689 -4.924435 -6.156093 -7.147080 -6.747988 -5.291275 -6.090125 -5.646500 -4.580594 -2.345175 -0.445177 0.031729 0.581069 -0.179771 0.811313 -0.673239 0.387726 -0.766354 -4.022689 -5.056932 -5.953048 -6.945648 -7.454075 -6.654609 -4.643821 -5.372699 -5.030400 -4.281512 -2.760815 -1.436678 -1.157933 -0.793535 -1.092515 0.163790 -0.675345 0.359879 -1.652825 -4.470759 -5.564539 -6.492546 -7.329397 -7.616100 -6.556279 -4.032357 -4.812712 -4.677238 -4.303039 -3.457671 -2.640433 -2.228299 -2.232287 -2.346483 -2.429664 -2.333797 -2.550842 -3.926314 -5.060157 -5.932031 -6.777947 -7.497012 -7.692733 -6.453141 -3.446607 -4.270698 -4.277968 -4.147215 -3.764865 -3.408069 -3.306973 -3.412213 -3.716982 -4.079512 -4.320963 -4.632216 -5.179785 -5.845574 -6.429202 -7.035999 -7.547936 -7.646075 -6.260651 -2.955031 -3.794684 -3.886808 -3.885469 -3.774230 -3.734094 -3.898015 -4.210289 -4.627915 -5.054640 -5.390232 -5.694011 -6.029078 -6.395766 -6.768889 -7.149715 -7.421471 -7.439493 -5.981028 -1.685970 -2.364422 -2.561347 -2.768720 -2.968471 -3.219516 -3.544110 -3.908384 -4.275984 -4.613316 -4.886543 -5.103386 -5.271198 ...)
(InitialTransformParametersFileName "C:\\Users\\andra\\AppData\\Local\\Temp\\Slicer\\Elastix\\20190808_122649_419\\result-transform\\TransformParameters.0.txt")
(UseBinaryFormatForTransformationParameters "false")
(HowToCombineTransforms "Compose")
...
// BSplineTransform specific
(GridSize 19 19 13)
(GridIndex 0 0 0)
(GridSpacing 16.3635271922 16.4510603777 16.8887922134)
(GridOrigin -139.5106562489 -143.1800706035 -101.3473427693)
(GridDirection 1.0000000000 0.0000000000 0.0000000000 0.0000000000 1.0000000000 0.0000000000 0.0000000000 0.0000000000 1.0000000000)
(BSplineTransformSplineOrder 3)
(UseCyclicTransform "false")

    """
    f = open(filename, 'r')
    fileContents = f.read()
    f.close()
    fileContents = fileContents.split("\n")

    transformType = self.getElastixParameters(fileContents, "Transform")[0]

    if transformType != "BSplineTransform":
      return False

    import numpy as np

    transformParams = self.getElastixParameters(fileContents, "TransformParameters", type="float")
    gridSize = self.getElastixParameters(fileContents, "GridSize", type="int")
    gridIndex = self.getElastixParameters(fileContents, "GridIndex", type="int")
    gridSpacing = self.getElastixParameters(fileContents, "GridSpacing", type="float")
    gridOrigin_LPS = self.getElastixParameters(fileContents, "GridOrigin", type="float")
    gridDirection_LPS = np.array(self.getElastixParameters(fileContents, "GridDirection", type="float")).reshape(3,3)

    bsplineCoefficients = vtk.vtkImageData()
    bsplineCoefficients.SetOrigin(-gridOrigin_LPS[0], -gridOrigin_LPS[1], gridOrigin_LPS[2])
    bsplineCoefficients.SetSpacing(gridSpacing)

    bsplineCoefficients.SetExtent(gridIndex[0], gridIndex[0]+gridSize[0]-1,
      gridIndex[1], gridIndex[1]+gridSize[1]-1,
      gridIndex[2], gridIndex[2]+gridSize[2]-1,)
    bsplineCoefficients.AllocateScalars(vtk.VTK_DOUBLE, 3)

    bsplineCoefficientsVoxelsArray_LPS = np.array(transformParams).reshape([3,int(len(transformParams)/3)])
    bsplineCoefficientsVoxelsArray_RAS = vtk.util.numpy_support.vtk_to_numpy(bsplineCoefficients.GetPointData().GetScalars())
    bsplineCoefficientsVoxelsArray_RAS[:,0] = -bsplineCoefficientsVoxelsArray_LPS[0,:]
    bsplineCoefficientsVoxelsArray_RAS[:,1] = -bsplineCoefficientsVoxelsArray_LPS[1,:]
    bsplineCoefficientsVoxelsArray_RAS[:,2] = bsplineCoefficientsVoxelsArray_LPS[2,:]
    bsplineCoefficients.GetPointData().GetScalars().Modified()

    gridDirection_LPS4 = np.eye(4)
    gridDirection_LPS4[0:3,0:3] = gridDirection_LPS
    ras2lps = np.array([[-1,0,0,0],[0,-1,0,0],[0,0,1,0],[0,0,0,1]])
    gridDirection_RAS = vtkMatrixFromArray(np.dot(ras2lps, gridDirection_LPS4))

    bsplineTransform = slicer.vtkOrientedBSplineTransform()
    bsplineTransform.SetBorderModeToZero()
    bsplineTransform.SetCoefficientData(bsplineCoefficients)
    bsplineTransform.SetGridDirectionMatrix(gridDirection_RAS)

    outputGeneralTransform.Concatenate(bsplineTransform)

    # Apply initial transform
    initialTransformFilename = self.getElastixInitialTransform(fileContents)
    if initialTransformFilename:
      return self.readElastixTransformToVTK(initialTransformFilename, outputGeneralTransform)
    else:
      return True

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
    fixedVolumeMaskNode = None, movingVolumeMaskNode = None, forceDisplacementFieldOutputTransform = True):

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
      # Save original file paths
      originalFilePath = ""
      originalFilePaths = []
      volumeStorageNode = volumeNode.GetStorageNode()
      if volumeStorageNode:
        originalFilePath = volumeStorageNode.GetFileName()
        for fileIndex in range(volumeStorageNode.GetNumberOfFileNames()):
          originalFilePaths.append(volumeStorageNode.GetNthFileName(fileIndex))
      # Save to new location
      filePath = os.path.join(inputDir, filename)
      slicer.util.saveNode(volumeNode, filePath, {"useCompression": False})
      inputParamsElastix.append(paramName)
      inputParamsElastix.append(filePath)
      # Restore original file paths
      if volumeStorageNode:
        volumeStorageNode.ResetFileNameList()
        volumeStorageNode.SetFileName(originalFilePath)
        for fileIndex in range(volumeStorageNode.GetNumberOfFileNames()):
          volumeStorageNode.AddFileName(originalFilePaths[fileIndex])
      else:
        # temporary storage node was created, remove it to restore original state
        volumeStorageNode = volumeNode.GetStorageNode()
        slicer.mrmlScene.RemoveNode(volumeStorageNode)

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

      transformFileName = resultTransformDir+'/TransformParameters.'+str(len(parameterFilenames)-1)+'.txt'

      #Load Linear Transform if available
      elastixTransformFileImported = False
      if outputTransformNode and (not forceDisplacementFieldOutputTransform):
        try:
          transformFromParent = vtk.vtkGeneralTransform()
          self.readElastixTransformToVTK(transformFileName, transformFromParent)
          # Save transform into transform node (as a simple matrix, if possible)
          transformFromParentLinear = vtk.vtkTransform()
          if slicer.vtkMRMLTransformNode.IsGeneralTransformLinear(transformFromParent, transformFromParentLinear):
            outputTransformNode.SetMatrixTransformFromParent(transformFromParentLinear.GetMatrix())
          else:
            outputTransformNode.SetAndObserveTransformFromParent(transformFromParent)
          elastixTransformFileImported = True
        except:
          # Could not load transform (probably not linear and bspline)
          elastixTransformFileImported = False

      #Create temp results directory
      resultResampleDir = os.path.join(tempDir, 'result-resample')
      qt.QDir().mkpath(resultResampleDir)
      inputParamsTransformix = []
      inputParamsTransformix += ['-tp', transformFileName]
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
          loadedOutputTransformNode = slicer.util.loadTransform(outputTransformPath)
          if loadedOutputTransformNode.GetReadAsTransformToParent():
            outputTransformNode.SetAndObserveTransformToParent(loadedOutputTransformNode.GetTransformToParent())
          else:
            outputTransformNode.SetAndObserveTransformFromParent(loadedOutputTransformNode.GetTransformFromParent())
          slicer.mrmlScene.RemoveNode(loadedOutputTransformNode)
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

# TODO: These functions were copied here from slicer.util so that this module can be used in Slicer-4.10
# Remove these, once Slicer-4.10 support is not needed anymore.

def vtkMatrixFromArray(narray):
  """Create VTK matrix from a 3x3 or 4x4 numpy array.
  :param narray: input numpy array
  The returned matrix is just a copy and so any modification in the array will not affect the output matrix.
  To set numpy array from VTK matrix, use :py:meth:`arrayFromVTKMatrix`.
  """
  from vtk import vtkMatrix4x4
  from vtk import vtkMatrix3x3
  narrayshape = narray.shape
  if narrayshape == (4,4):
    vmatrix = vtkMatrix4x4()
    updateVTKMatrixFromArray(vmatrix, narray)
    return vmatrix
  elif narrayshape == (3,3):
    vmatrix = vtkMatrix3x3()
    updateVTKMatrixFromArray(vmatrix, narray)
    return vmatrix
  else:
    raise RuntimeError("Unsupported numpy array shape: "+str(narrayshape)+" expected (4,4)")

def updateVTKMatrixFromArray(vmatrix, narray):
  """Update VTK matrix values from a numpy array.
  :param vmatrix: VTK matrix (vtkMatrix4x4 or vtkMatrix3x3) that will be update
  :param narray: input numpy array
  To set numpy array from VTK matrix, use :py:meth:`arrayFromVTKMatrix`.
  """
  from vtk import vtkMatrix4x4
  from vtk import vtkMatrix3x3
  if isinstance(vmatrix, vtkMatrix4x4):
    matrixSize = 4
  elif isinstance(vmatrix, vtkMatrix3x3):
    matrixSize = 3
  else:
    raise RuntimeError("Output vmatrix must be vtk.vtkMatrix3x3 or vtk.vtkMatrix4x4")
  if narray.shape != (matrixSize, matrixSize):
    raise RuntimeError("Input narray size must match output vmatrix size ({0}x{0})".format(matrixSize))
  vmatrix.DeepCopy(narray.ravel())

