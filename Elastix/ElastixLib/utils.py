import slicer
import qt


def showFolder(path):
  qt.QDesktopServices().openUrl(qt.QUrl("file:///" + path, qt.QUrl.TolerantMode))


def createTempDirectory():
  tempDir = qt.QDir(getTempDirectoryBase())
  tempDirName = qt.QDateTime().currentDateTime().toString("yyyyMMdd_hhmmss_zzz")
  fileInfo = qt.QFileInfo(qt.QDir(tempDir), tempDirName)
  return createDirectory(fileInfo.absoluteFilePath())


def getTempDirectoryBase():
  tempDir = qt.QDir(slicer.app.temporaryPath)
  fileInfo = qt.QFileInfo(qt.QDir(tempDir), "Elastix")
  return createDirectory(fileInfo.absoluteFilePath())


def createDirectory(path):
  if qt.QDir().mkpath(path):
    return path
  else:
    raise RuntimeError(f"Failed to create directory {path}")


def getContentSuffixes(content, presets):
  numbers = []
  for oPreset in presets:
    oContent = oPreset.getContent()
    if content == oContent or oContent.startswith(content):
      if oContent.startswith(content):
        stripped = oContent.replace(content, "").strip()
        if stripped.isdigit():
          numbers.append(int(stripped))
  return numbers