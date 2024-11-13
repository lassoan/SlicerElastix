import logging
import shutil

import qt
import vtk

import abc
import os

from typing import Callable

import slicer
from pathlib import Path
from ElastixLib.preset import Preset, UserPreset, createPreset


class ElastixDatabase(abc.ABC):

  @property
  def logCallback(self):
    return self._logCallback

  @logCallback.setter
  def logCallback(self, cb: Callable = None):
    self._logCallback = cb

  def getRegistrationPresetsFromXML(self, elastixParameterSetDatabasePath, presetClass):
    if not os.path.isfile(elastixParameterSetDatabasePath):
      raise ValueError("Failed to open parameter set database: " + elastixParameterSetDatabasePath)
    elastixParameterSetDatabaseXml = vtk.vtkXMLUtilities.ReadElementFromFile(elastixParameterSetDatabasePath)

    # Create python list from XML for convenience
    registrationPresets = []
    if elastixParameterSetDatabaseXml is not None:
      for parameterSetIndex in range(elastixParameterSetDatabaseXml.GetNumberOfNestedElements()):
        parameterSetXml = elastixParameterSetDatabaseXml.GetNestedElement(parameterSetIndex)
        parameterFilesXml = parameterSetXml.FindNestedElementWithName('ParameterFiles')
        parameterFiles = []
        for parameterFileIndex in range(parameterFilesXml.GetNumberOfNestedElements()):
          parameterFiles.append(os.path.join(
            str(Path(elastixParameterSetDatabasePath).parent),
            parameterFilesXml.GetNestedElement(parameterFileIndex).GetAttribute('Name'))
          )
        parameterSetAttributes = \
          [parameterSetXml.GetAttribute(attr) if parameterSetXml.GetAttribute(attr) is not None else "" for attr in ['id', 'modality', 'content', 'description', 'publications']]
        try:
          registrationPresets.append(
            createPreset(*parameterSetAttributes, parameterFiles=parameterFiles, presetClass=presetClass)
          )
        except FileNotFoundError as exc:
          msg = f"Cannot load preset. Loading failed with error: {exc}"
          logging.error(msg)
          if self.logCallback:
            self.logCallback(msg)
          continue
    return registrationPresets

  def __init__(self):
    self._logCallback = None
    self.registrationPresets = None

  def getRegistrationPresets(self, force_refresh=False):
    if self.registrationPresets and not force_refresh:
      return self.registrationPresets

    self.registrationPresets = self._getRegistrationPresets()

    return self.registrationPresets

  @abc.abstractmethod
  def _getRegistrationPresets(self):
    pass


class BuiltinElastixDatabase(ElastixDatabase):

  # load txt files into slicer scene
  DATABASE_FILE = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Resources', 'RegistrationParameters',
                 'ElastixParameterSetDatabase.xml'))

  def getPresetsDir(self):
    return str(Path(self.DATABASE_FILE).parent)

  def _getRegistrationPresets(self):
    return self.getRegistrationPresetsFromXML(self.DATABASE_FILE, presetClass=Preset)


class UserElastixDataBase(ElastixDatabase):

  DATABASE_LOCATION = Path(slicer.app.slicerUserSettingsFilePath).parent / "Elastix"

  @staticmethod
  def getAllXMLFiles(directory):
    import fnmatch
    files = []
    for root, dirnames, filenames in os.walk(directory):
      for filename in fnmatch.filter(filenames, '*{}'.format(".xml")):
        files.append(os.path.join(root, filename))
    return files

  def __init__(self):
    self.DATABASE_LOCATION.mkdir(exist_ok=True)
    self._presetLocations = {}
    super().__init__()

  def getPresetsDir(self):
    return str(self.DATABASE_LOCATION)

  def _getRegistrationPresets(self):
    xml_files = self.getAllXMLFiles(self.DATABASE_LOCATION)
    registrationPresets = []
    for xml_file in xml_files:
      presets = self.getRegistrationPresetsFromXML(xml_file, presetClass=UserPreset)
      if len(presets) > 1:
        raise RuntimeError("The User presets are intended to have one preset per .xml file only.")
      for preset in presets:
        self._presetLocations[preset] = str(Path(xml_file).parent)
      registrationPresets.extend(presets)
    return registrationPresets

  def deletePreset(self, preset: UserPreset):
    path = self._presetLocations.pop(preset)
    shutil.rmtree(path)


class InSceneElastixDatabase(ElastixDatabase):

  def _getRegistrationPresets(self):
    registrationPresets = []

    nodes = filter(lambda n: n.GetAttribute('Type') == 'ElastixPreset',
           slicer.util.getNodesByClass('vtkMRMLTextNode'))

    from ElastixLib.preset import getInScenePreset
    for node in nodes:
      registrationPresets.append(getInScenePreset(node))

    return registrationPresets
