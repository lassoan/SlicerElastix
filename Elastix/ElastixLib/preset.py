import os
import json
from pathlib import Path

from ElastixLib.utils import createTempDirectory

import slicer
from typing import List, Union, Dict

# for caching instead of persistently creating new preset for each node in the scene
InScenePresets = {}

ID_KEY = "id"
MODALITY_KEY = "modality"
DESCRIPTION_KEY = "description"
CONTENT_KEY = "content"
PUBLICATIONS_KEY = "publications"
PARAMETER_FILES_KEY = "parameter_files"
NAME_KEY = "name"


class Preset:

  def __init__(self):
    self._data = {}

  def getName(self):
    return f"{self.getModality()} ({self.getContent()})"

  def getID(self):
    return self._getDictAttribute(ID_KEY)

  def setID(self, value: str):
    self._data[ID_KEY] = value

  def getModality(self):
    return self._getDictAttribute(MODALITY_KEY)

  def setModality(self, value: str):
    self._data[MODALITY_KEY] = value

  def getContent(self) -> str:
    return self._getDictAttribute(CONTENT_KEY)

  def setContent(self, value: str):
    self._data[CONTENT_KEY] = value

  def getDescription(self) -> str:
    return self._getDictAttribute(DESCRIPTION_KEY)

  def setDescription(self, value: str):
    self._data[DESCRIPTION_KEY] = value

  def getPublications(self) -> str:
    return self._getDictAttribute(PUBLICATIONS_KEY)

  def setPublications(self, value: str):
    self._data[PUBLICATIONS_KEY] = value

  def setParameters(self, values: List[Dict[str, str]]):
    self._data[PARAMETER_FILES_KEY] = values

  def getParameterFiles(self):
    tempDir = createTempDirectory()
    filenames = []
    for param in self.getParameters():
      name = param[NAME_KEY]
      if not name.endswith('.txt'):
        name += '.txt'
      filename = os.path.join(tempDir, name)
      with open(filename, 'w') as file:
        file.write(param[CONTENT_KEY])
      filenames.append(filename)
    return filenames

  def getParameters(self):
    return self._getDictAttribute(PARAMETER_FILES_KEY, [])

  def getParameterSectionNames(self) -> List:
    return [pf[NAME_KEY] for pf in self._data[PARAMETER_FILES_KEY]]

  def addParameterSection(self, name, content: Union[str]):
    parameters = self.getParameters()
    parameters.append(
      {
        NAME_KEY: name,
        CONTENT_KEY: content
      }
    )

  def hasParameterSection(self, name):
    parameters = self.getParameters()
    for param in parameters:
      if param[NAME_KEY] == name:
        return True
    return False

  def removeParameterSection(self, idx):
    parameters = self.getParameters()
    parameters.pop(idx)

  def getParameterSectionIndex(self, name):
    parameters = self.getParameters()
    for secIdx, param in enumerate(parameters):
      if param[NAME_KEY] == name:
        return secIdx
    return -1

  def getParameterSectionContent(self, name):
    parameters = self.getParameters()
    for param in parameters:
      if param[NAME_KEY] == name:
        return param[CONTENT_KEY]
    return ""

  def getParameterSectionByIdx(self, idx):
    parameters = self.getParameters()
    return parameters[idx]

  def getParameterSectionContentByIdx(self, idx):
    return self.getParameterSectionByIdx(idx)[CONTENT_KEY]

  def getMetaInformation(self, keys):
    return {key: self._data[key] for key in keys}

  def _getDictAttribute(self, key, default=""):
    try:
      return self._data[key]
    except KeyError:
      self._data[key] = default
      return self._data[key]

  def toJSON(self):
    return json.dumps(self._data, indent=2)


class UserPreset(Preset):
  pass


class InScenePreset(Preset):

  @staticmethod
  def createTextNode():
    presetNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLTextNode")
    presetNode.SetAttribute("Type", "ElastixPreset")
    return presetNode

  def __init__(self, presetNode: slicer.vtkMRMLTextNode = None):
    super().__init__()

    """ Creates new scripted node if none was defined

    :param presetNode:
    """
    if not presetNode:
      presetNode = self.createTextNode()
    self.setPresetNode(presetNode)

  def delete(self):
    slicer.mrmlScene.RemoveNode(self._presetNode)

  def setPresetNode(self, node: slicer.vtkMRMLTextNode):
    if node and not node.GetAttribute("Type") == "ElastixPreset":
      raise AttributeError(f"Provided node {node.GetID()} needs to be of type 'ElastixPreset'")

    self._presetNode = node

    if self._presetNode:
      shNode = slicer.vtkMRMLSubjectHierarchyNode.GetSubjectHierarchyNode(slicer.mrmlScene)
      if self._presetNode.GetHideFromEditors():
        self._presetNode.SetHideFromEditors(False)
        shNode.RequestOwnerPluginSearch(self._presetNode)
        shNode.SetItemAttribute(shNode.GetItemByDataNode(self._presetNode), "Type", "ElastixPreset")

    self._readFromTextNode()

  def getPresetNode(self) -> slicer.vtkMRMLTextNode:
    return self._presetNode

  def _updateTextNode(self):
    self._presetNode.SetText(
      json.dumps(self._data, indent=2)
    )
    self._presetNode.SetName(self.getName())

  def _readFromTextNode(self):
    text = self._presetNode.GetText()
    self._data = json.loads(text) if text else {}

  def setID(self, value):
    super().setID(value)
    self._updateTextNode()

  def setModality(self, value):
    super().setModality(value)
    self._updateTextNode()

  def setContent(self, value: str):
    super().setContent(value)
    self._updateTextNode()

  def setDescription(self, value: str):
    super().setDescription(value)
    self._updateTextNode()

  def setPublications(self, value: str):
    super().setPublications(value)
    self._updateTextNode()

  def setParameters(self, values: List[Dict[str, str]]):
    super().setParameters(values)
    self._updateTextNode()

  def addParameterSection(self, name, content: Union[str]):
    super().addParameterSection(name, content)
    self._updateTextNode()

  def setParameterSectionContentByIdx(self, idx, content):
    section = self.getParameterSectionByIdx(idx)
    section[CONTENT_KEY] = content
    self._updateTextNode()

  def removeParameterSection(self, idx):
    super().removeParameterSection(idx)
    self._updateTextNode()

  def moveParameterSection(self, fromIdx, toIdx):
    parameters = self.getParameters()
    parameters.insert(toIdx, parameters.pop(fromIdx))
    self._updateTextNode()


def getInScenePreset(presetNode: slicer.vtkMRMLTextNode):
  if presetNode is None:
    return None

  try:
    preset = InScenePresets[presetNode]
  except KeyError:
    preset = InScenePreset(presetNode)

    InScenePresets[presetNode] = preset
  return preset


def createPreset(id:str, modality:str, content:str, description:str, publications:str, parameterFiles: List[str] = None, presetClass=Preset):
  if parameterFiles is None:
    parameterFiles = []

  preset = presetClass()
  preset.setID(id)
  preset.setModality(modality)
  preset.setContent(content)
  preset.setDescription(description)
  preset.setPublications(publications)

  for f in parameterFiles:
    with open(f, 'r') as file:
      file_content = file.read()
      preset.addParameterSection(
        Path(f).name,
        file_content
      )

  return preset


def copyPreset(preset: Preset) -> InScenePreset:
  """ takes any preset and generates a InScenePreset from it

  :param preset:
  :return: instance of InScenePreset
  """
  presetCopy = InScenePreset()
  presetCopy.setID(generateID(preset.getID()))
  presetCopy.setModality(preset.getModality())
  presetCopy.setContent(preset.getContent())
  presetCopy.setDescription(preset.getDescription())
  presetCopy.setPublications(preset.getPublications())

  import copy
  presetCopy.setParameters(copy.deepcopy(preset.getParameters()))
  return presetCopy


def generateID(presetID):
  hook = "-#"
  if hook in presetID:
    presetID = presetID[:presetID.find(hook)]

  import random
  import base64
  return f"{presetID}-#{base64.urlsafe_b64encode(random.randbytes(6)).decode()}"


def isWritable(preset: Preset):
  return isinstance(preset, InScenePreset)


def canDelete(preset: Preset):
  return isinstance(preset, InScenePreset) or isinstance(preset, UserPreset)


def getPresetType(preset: Preset):
  if isinstance(preset, UserPreset):
    return "user preset"
  elif isinstance(preset, InScenePreset):
    return "stored in scene"
  elif isinstance(preset, Preset):
    return "built-in preset"
  else:
    return "unknown"
