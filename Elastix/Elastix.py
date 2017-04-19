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
    presets = self.logic.getRegistrationPresets()
    for preset in presets:
      self.registrationPresetSelector.addItem(preset['name'], preset['id'])
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
    # output transform selector
    #
    self.outputTransformSelector = slicer.qMRMLNodeComboBox()
    self.outputTransformSelector.nodeTypes = ["vtkMRMLTransformNode", "vtkMRMLLinearTransformNode"]
    self.outputTransformSelector.selectNodeUponCreation = True
    self.outputTransformSelector.addEnabled = True
    self.outputTransformSelector.removeEnabled = True
    self.outputTransformSelector.noneEnabled = True
    self.outputTransformSelector.showHidden = False
    self.outputTransformSelector.showChildNodeTypes = False
    self.outputTransformSelector.setMRMLScene( slicer.mrmlScene )
    self.outputTransformSelector.setToolTip( "(optional) Computed resampling transform that transform nodes from moving volume space to fixed volume space. NOTE: You must set at least one output object (transform and/or output volume)." )
    outputParametersFormLayout.addRow("Output transform: ", self.outputTransformSelector)

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
    # Apply Button
    #
    self.applyButton = qt.QPushButton("Apply")
    self.applyButton.toolTip = "Run the algorithm."
    self.applyButton.enabled = False
    self.layout.addWidget(self.applyButton)

    # connections
    self.applyButton.connect('clicked(bool)', self.onApplyButton)
    self.fixedVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)
    self.outputVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)

    # Add vertical spacer
    self.layout.addStretch(1)

    # Refresh Apply button state
    self.onSelect()

  def cleanup(self):
    pass

  def onSelect(self):
    self.applyButton.enabled = self.fixedVolumeSelector.currentNode() and self.outputVolumeSelector.currentNode()

  def onApplyButton(self):
    self.logic = ElastixLogic()
                  
    presets = self.logic.getRegistrationPresets()
    parameterFileNames = presets[self.registrationPresetSelector.currentIndex]['parameterFiles']
    parameterFilePaths = []
    for parameterFileName in parameterFileNames:
      parameterFilePaths.append(os.path.join(self.logic.registrationParameterFilesDir, parameterFileName))
      
    self.logic.registerVolumes(self.fixedVolumeSelector.currentNode(), self.movingVolumeSelector.currentNode(),
      parameterFilePaths, self.outputTransformSelector.currentNode(), self.outputVolumeSelector.currentNode())

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
    import os
    self.scriptPath = os.path.dirname(os.path.abspath(__file__))
    self.registrationParameterFilesDir = os.path.abspath(os.path.join(self.scriptPath, 'Resources', 'RegistrationParameters'))
    self.elastixBinDir = os.path.abspath(os.path.join(self.scriptPath, '../../../bin'))
    
    import platform
    executableExt = '.exe' if platform.system() == 'Windows' else ''
    self.elastixPath = os.path.join(self.elastixBinDir, 'elastix' + executableExt)
    self.transformixPath = os.path.join(self.elastixBinDir, 'transformix' + executableExt)
    
    # Verify that required files are found
    for requiredFile in [self.elastixPath, self.transformixPath]:
      if not os.path.isfile(requiredFile):
        logging.error('Required elastix file not found at' + requiredFile)
    
    # Create an environment for elastix where executables are added to the path
    self.elastixEnv = os.environ.copy()
    self.elastixEnv["PATH"] = self.elastixBinDir + os.pathsep + self.elastixEnv["PATH"]
    
  def getRegistrationPresets(self):
    presets = []
    presets.append({ 'id': 'par000', 'name': 'Default', 'modality': 'all', 'content': 'all', 'parameterFiles': ['Par0000affine.txt', 'Par0000bspline.txt'] })
    presets.append({ 'id': 'par001', 'name': 'Brain MR T1', 'modality': '3D MR T1, monomodal', 'content': 'brain', 'parameterFiles': ['Par0001affine.txt', 'Par0001bspline.txt']})
    presets.append({ 'id': 'par002', 'name': 'Prostate MR', 'modality': '3D MR BFFE, monomodal', 'content': 'prostate', 'parameterFiles': ['Par0002affine.txt', 'Par0002bspline.txt']})
    return presets

  def startElastix(self, cmdLineArguments):
    import subprocess
    #stdout=subprocess.PIPE, stderr=subprocess.PIPE
    return subprocess.Popen([self.elastixPath] + cmdLineArguments, env=self.elastixEnv)

  def startTransformix(self, cmdLineArguments):
    import subprocess
    #stdout=subprocess.PIPE, stderr=subprocess.PIPE
    return subprocess.Popen([self.transformixPath] + cmdLineArguments, env=self.elastixEnv)
  
  def tempDirectory(self):
    import qt, slicer
    tempDir = qt.QDir(slicer.app.temporaryPath)
    tempDirName = qt.QDateTime().currentDateTime().toString("yyyy-MM-dd_hh+mm+ss.zzz")
    fileInfo = qt.QFileInfo(qt.QDir(tempDir), tempDirName)
    dirPath = fileInfo.absoluteFilePath()
    qt.QDir().mkpath(dirPath)
    return dirPath 
  
  def registerVolumes(self, fixedVolumeNode, movingVolumeNode, parameterFiles, outputTransformNode, outputVolumeNode):
    tempDir = self.tempDirectory() # slicer.util.tempDirectory() has a bug, does not append datetime
    logging.info('registerVolumes started - working directory: '+tempDir)
    import shutil

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
    for parameterFile in parameterFiles:
      inputParamsElastix.append('-p')
      inputParamsElastix.append(parameterFile)
    ep = self.startElastix(inputParamsElastix)
    ep.communicate()

    # Resample
    resultResampleDir = os.path.join(tempDir, 'result-resample')
    qt.QDir().mkpath(resultResampleDir)
    inputParamsTransformix = ['-in', movingVolumePath, '-out', resultResampleDir]
    if outputTransformNode:
      inputParamsTransformix += ['-def', 'all']
    if outputVolumeNode:
      inputParamsTransformix += ['-tp', resultTransformDir+'/TransformParameters.'+str(len(parameterFiles)-1)+'.txt']
    tp = self.startTransformix(inputParamsTransformix)
    tp.communicate()

    if outputVolumeNode:
      outputVolumePath = os.path.join(resultResampleDir, "result.mhd")
      [success, loadedOutputVolumeNode] = slicer.util.loadVolume(outputVolumePath, returnNode = True)
      if success:
        outputVolumeNode.SetAndObserveImageData(loadedOutputVolumeNode.GetImageData())
        ijkToRas = vtk.vtkMatrix4x4()
        loadedOutputVolumeNode.GetIJKToRASMatrix(ijkToRas)
        outputVolumeNode.SetIJKToRASMatrix()
        slicer.mrmlScene.RemoveNode(loadedOutputVolumeNode)

    if outputTransformNode:
      outputTransformPath = os.path.join(resultResampleDir, "deformationField.mhd")
      [success, loadedOutputTransformNode] = slicer.util.loadTransform(outputTransformPath, returnNode = True)
      if success:
        outputTransformNode.SetAndObserveImageData(loadedOutputVolumeNode.GetImageData())
        ijkToRas = vtk.vtkMatrix4x4()
        loadedOutputVolumeNode.GetIJKToRASMatrix(ijkToRas)
        outputTransformNode.SetIJKToRASMatrix()
        slicer.mrmlScene.RemoveNode(loadedOutputVolumeNode)

        
    # remove temp directory
    # shutil.rmtree(tempDir) 
    
  def isValidInputOutputData(self, inputVolumeNode, outputVolumeNode):
    """Validates if the output is not the same as input
    """
    if not inputVolumeNode:
      logging.debug('isValidInputOutputData failed: no input volume node defined')
      return False
    if not outputVolumeNode:
      logging.debug('isValidInputOutputData failed: no output volume node defined')
      return False
    if inputVolumeNode.GetID()==outputVolumeNode.GetID():
      logging.debug('isValidInputOutputData failed: input and output volume is the same. Create a new volume for output to avoid this error.')
      return False
    return True

  def run(self, inputVolume, outputVolume, imageThreshold, enableScreenshots=0):
    """
    Run the actual algorithm
    """

    if not self.isValidInputOutputData(inputVolume, outputVolume):
      slicer.util.errorDisplay('Input volume is the same as output volume. Choose a different output volume.')
      return False

    logging.info('Processing started')

    # Compute the thresholded output volume using the Threshold Scalar Volume CLI module
    cliParams = {'InputVolume': inputVolume.GetID(), 'OutputVolume': outputVolume.GetID(), 'ThresholdValue' : imageThreshold, 'ThresholdType' : 'Above'}
    cliNode = slicer.cli.run(slicer.modules.thresholdscalarvolume, None, cliParams, wait_for_completion=True)

    # Capture screenshot
    if enableScreenshots:
      self.takeScreenshot('ElastixTest-Start','MyScreenshot',-1)

    logging.info('Processing completed')

    return True


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
    #
    
    logic = ElastixLogic()
       
    ep = logic.startElastix([
      '-f', r'c:\D\SE\Elastix\Resources\MRBrainTumor1.nrrd',
      '-m', r'c:\D\SE\Elastix\Resources\MRBrainTumor2.nrrd',
      '-p', r'c:\D\SE\Elastix\Resources\Par0000affine.txt',
      '-p', r'c:\D\SE\Elastix\Resources\Par0000bspline.txt',
      '-out', r'c:\D\SE\Elastix\Resources'])
    ep.communicate()

    tp = logic.startTransformix([
      '-in', r'c:\D\SE\Elastix\Resources\MRBrainTumor2.nrrd',
      '-out', r'c:\D\SE\Elastix\Resources\result',
      '-tp', r'c:\D\SE\Elastix\Resources\TransformParameters.1.txt',
      '-def', 'all'])
    tp.communicate()


    # while True:
    # slicer.app.processEvents() # force update
    # out = process.stdout.read(1)
    # err = process.stderr.read(1)
    # if err == '' and out == '' and process.poll() != None:
        # break
    # if out != '':
        # sys.stdout.write(out)
        # sys.stdout.flush()
    # if err != '':
        # sys.stdout.write(err)
        # sys.stdout.flush()

    
    #self.assertIsNotNone( logic.hasImageData(volumeNode) )
    self.delayDisplay('Test passed!')
