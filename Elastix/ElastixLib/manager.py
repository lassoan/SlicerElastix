import os
import qt
import slicer
from .constants import *


class PathLineEditDelegate(qt.QItemDelegate):
  def __init__(self, parent):
    qt.QItemDelegate.__init__(self, parent)

  def createEditor(self, parent, option, index):
    import ctk
    pathLineEdit = ctk.ctkPathLineEdit(parent)
    pathLineEdit.filters = ctk.ctkPathLineEdit.Files
    pathLineEdit.nameFilters = ["*.txt"]
    return pathLineEdit

  def setEditorData(self, editor, index):
    editor.blockSignals(True)
    editor.currentPath = index.model().data(index) if index.model().data(index) else ''
    editor.blockSignals(False)

  def setModelData(self, editor, model, index):
    model.setData(index, editor.currentPath)


def makeAction(parent, text, slot, icon=None):
  action = qt.QAction(text, parent)
  action.connect('triggered(bool)', slot)

  if icon is not None:
    action.setIcon(slicer.app.style().standardIcon(icon))

  parent.addAction(action)
  return action


class NewPresetDialog:

  @property
  def selectionModel(self):
    return self.ui.tableView.selectionModel()

  def __init__(self):
    from Elastix import ElastixLogic
    self.elastixLogic = ElastixLogic()
    self.setup()

  def setup(self):
    scriptedModulesPath = os.path.dirname(slicer.util.modulePath("Elastix"))
    self.widget = slicer.util.loadUI(os.path.join(scriptedModulesPath, 'Resources', "UI/NewPresetDialog.ui"))
    self.ui = slicer.util.childWidgetVariables(self.widget)

    self.ui.presetSelector.addItem('')
    for preset in self.elastixLogic.getRegistrationPresets():
      self.ui.presetSelector.addItem(f"{preset[RegistrationPresets_Modality]} ({preset[RegistrationPresets_Content]})")

    self.model = qt.QStandardItemModel(1, 1)
    self.ui.tableView.setModel(self.model)
    self.ui.tableView.setItemDelegateForColumn(0, PathLineEditDelegate(self.model))
    self.model.removeRows(0, self.model.rowCount())

    # configure buttons
    self.ui.addButton.clicked.connect(self.onAddButton)
    self.ui.removeButton.clicked.connect(self.onRemoveButton)

    self.ui.moveUpButton.clicked.connect(self.onMoveUpButton)
    self.ui.moveDownButton.clicked.connect(self.onMoveDownButton)
    self.ui.buttonBox.clicked.connect(self.onResetButton)

    self.model.connect('rowsInserted(QModelIndex,int,int)', self.updateGUI)
    self.model.connect('rowsRemoved(QModelIndex,int,int)', self.updateGUI)
    self.model.connect('dataChanged(QModelIndex,QModelIndex)', self.updateGUI)

    self.ui.idBox.textChanged.connect(self.updateGUI)
    self.ui.modalityBox.textChanged.connect(self.updateGUI)
    self.ui.contentBox.textChanged.connect(self.updateGUI)
    self.ui.descriptionBox.textChanged.connect(self.updateGUI)

    self.selectionModel.selectionChanged.connect(self.updateGUI)

    self.ui.presetSelector.connect("activated(int)", self.onPresetSelected)

    self._openFileAction = makeAction(self.ui.toolButton, text="Open Parameter File", slot=self.onOpenFileAction,
                                      icon=qt.QStyle.SP_FileLinkIcon)
    self._openFileLocationAction = makeAction(self.ui.toolButton, text="Open Parameter File Location",
                                              slot=lambda: self.onOpenFileAction(location=True),
                                              icon=qt.QStyle.SP_DirLinkIcon)

  def fileForSelectionExists(self, modelIndex):
    item = self.model.item(modelIndex.row(), 0)
    if item:
      return os.path.exists(item.text())

  def onOpenFileAction(self, location=False):
    selectedRow = self.getSelectedRow()
    if selectedRow:
      item = self.model.item(selectedRow.row(), 0)
      from pathlib import Path
      filepath = Path(item.text()).parent if location is True else item.text()
      import subprocess, os, platform
      if platform.system() == 'Darwin':  # macOS
        subprocess.call(('open', filepath))
      elif platform.system() == 'Windows':  # Windows
        os.startfile(filepath)
      else:  # linux variants
        subprocess.call(('xdg-open', filepath))

  def onAddButton(self):
    self.model.insertRow(self.model.rowCount())
    self.ui.tableView.setCurrentIndex(self.model.index(self.model.rowCount() - 1, 0))

  def getSelectedRow(self):
    selectedRows = self.selectionModel.selectedRows()
    if selectedRows:
      return selectedRows[0]
    return None

  def onRemoveButton(self):
    selectedRow = self.getSelectedRow()
    if selectedRow:
      self.model.removeRow(selectedRow.row())

  def onMoveUpButton(self):
    selectedRow = self.getSelectedRow()
    if not selectedRow or selectedRow.row() == 0:
      # already top most row
      return
    self._moveItem(selectedRow.row(), selectedRow.row() - 1)
    self.ui.tableView.setCurrentIndex(self.model.index(selectedRow.row() - 1, 0))

  def onMoveDownButton(self):
    selectedRow = self.getSelectedRow()
    if not selectedRow or selectedRow.row() == self.model.rowCount() - 1:
      # already bottom most row
      return
    self._moveItem(selectedRow.row(), selectedRow.row() + 1)
    self.ui.tableView.setCurrentIndex(self.model.index(selectedRow.row() + 1, 0))

  def onResetButton(self, button):
    if button is self.ui.buttonBox.button(qt.QDialogButtonBox.Reset):
      self.resetForm()

  def resetForm(self):
    self.widget.done(4)

  def _moveItem(self, fromRow, toRow):
    fromItem = self.model.takeItem(fromRow, 0)
    toItem = self.model.takeItem(toRow, 0)
    self.model.setItem(toRow, 0, fromItem)
    self.model.setItem(fromRow, 0, toItem)

  def getParameterFiles(self):
    parameterFiles = []
    for rowIdx in range(self.model.rowCount()):
      item = self.model.item(rowIdx, 0)
      if item:
        parameterFiles.append(item.text())
    return parameterFiles

  def getMetaInformation(self):
    attributes = {}
    attributes['content'] = self.ui.contentBox.text
    attributes['description'] = self.ui.descriptionBox.text
    attributes['id'] = self.ui.idBox.text
    attributes['modality'] = self.ui.modalityBox.text
    attributes['publications'] = self.ui.publicationsBox.plainText
    return attributes

  def updateGUI(self):
    valiParameterFiles = self.model.rowCount() > 0 and all(
      self.model.item(rowIdx, 0) is not None for rowIdx in range(self.model.rowCount()))
    validFormData = valiParameterFiles and self.ui.modalityBox.text != '' \
                    and self.ui.contentBox.text != '' and self.ui.descriptionBox.text != ''
    idExists = self.ui.idBox.text in [preset[RegistrationPresets_Id] for preset in
                                      self.elastixLogic.getRegistrationPresets()]
    validId = self.ui.idBox.text != '' and not idExists
    self.ui.idBoxWarning.text = "*" if idExists else ''
    self.ui.buttonBox.button(qt.QDialogButtonBox.Ok).setEnabled(validId and validFormData)

    self.ui.warningLabel.text = "*ParameterSet with given id already exists" if idExists else ''
    selectedRow = self.getSelectedRow()
    self.ui.toolButton.setEnabled(selectedRow is not None and self.fileForSelectionExists(selectedRow))
    self.ui.removeButton.setEnabled(selectedRow is not None)
    self.ui.moveUpButton.setEnabled(selectedRow and selectedRow.row() > 0)
    self.ui.moveDownButton.setEnabled(selectedRow and selectedRow.row() < self.model.rowCount() - 1)

  def onPresetSelected(self):
    if self.ui.presetSelector.currentIndex == 0:
      return
    preset = self.elastixLogic.getRegistrationPresets()[self.ui.presetSelector.currentIndex - 1]
    self.autoPopulateFormFromPreset(preset)

  def autoPopulateFormFromPreset(self, preset):
    self.ui.idBox.text = preset[RegistrationPresets_Id]
    self.ui.modalityBox.text = preset[RegistrationPresets_Modality]
    self.ui.contentBox.text = preset[RegistrationPresets_Content]
    self.ui.descriptionBox.text = preset[RegistrationPresets_Description]
    self.ui.publicationsBox.plainText = preset[RegistrationPresets_Publications]

    self.model.removeRows(0, self.model.rowCount())
    for pIdx, paramFile in enumerate(preset[RegistrationPresets_ParameterFilenames]):
      self.onAddButton()
      modelIndex = self.model.index(pIdx, 0)
      databaseDir = self.elastixLogic.registrationParameterFilesDir
      self.model.setData(modelIndex, os.path.join(databaseDir, paramFile))

  def exec_(self):
    self.updateGUI()
    return self.widget.exec_()
