import qt, ctk, slicer
from AbstractScriptedSubjectHierarchyPlugin import *


class ElastixPresetSubjectHierarchyPlugin(AbstractScriptedSubjectHierarchyPlugin):

  # Necessary static member to be able to set python source to scripted subject hierarchy plugin
  filePath = __file__

  def __init__(self, scriptedPlugin):
    scriptedPlugin.name = 'Elastix'
    AbstractScriptedSubjectHierarchyPlugin.__init__(self, scriptedPlugin)

  def canAddNodeToSubjectHierarchy(self, node, parentItemID = None):
    if node is not None and node.IsA("vtkMRMLScriptedModuleNode"):
      if node.GetAttribute("Type") == "ElastixPreset":
        return 0.9
    return 0.0

  def canOwnSubjectHierarchyItem(self, itemID):
    pluginHandlerSingleton = slicer.qSlicerSubjectHierarchyPluginHandler.instance()
    shNode = pluginHandlerSingleton.subjectHierarchyNode()
    associatedNode = shNode.GetItemDataNode(itemID)
    return self.canAddNodeToSubjectHierarchy(associatedNode)

  def roleForPlugin(self):
    return "ElastixPreset"

  def icon(self, itemID):
    import os
    iconPath = None
    pluginHandlerSingleton = slicer.qSlicerSubjectHierarchyPluginHandler.instance()
    shNode = pluginHandlerSingleton.subjectHierarchyNode()
    associatedNode = shNode.GetItemDataNode(itemID)
    if associatedNode is not None and associatedNode.IsA("vtkMRMLScriptedModuleNode"):
      if associatedNode.GetAttribute("Type") == "ElastixPreset":
        iconPath = os.path.join(os.path.dirname(__file__), '../Resources/Icons/Elastix.png')
    if iconPath and os.path.exists(iconPath):
      return qt.QIcon(iconPath)
    # Item unknown by plugin
    return qt.QIcon()

  def tooltip(self, itemID):
    return "Elastix preset"