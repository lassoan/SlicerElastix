"""Registration in a web browser (SlicerWeb), where elastix cannot run as a program.

On the desktop the module writes the volumes to files and runs the elastix and transformix
programs on them. A web page cannot start a program; what it can do is run elastix compiled to
WebAssembly - the elastix of ITK-Wasm (https://github.com/InsightSoftwareConsortium/ITKElastix),
driven from Python by the itkwasm-elastix package - in a worker of the page, so that the views keep
drawing while it registers. This module is that path, and the files are the desktop's: the volumes
and the initial transform written by Slicer, the resampled volume and the transform read back by
it. The worker (ElastixLib/web_worker.py) reads and writes them with ITK-Wasm's image IO, and
writes the transform elastix computed as an Insight transform file (ElastixLib/web_itk_transform_io.py)
from its transform parameter maps.

What the desktop does and this cannot: masks (the ITK-Wasm elastix takes none yet), a displacement
field as the output transform (transformix in ITK-Wasm resamples images and does not write
deformation fields: the output transform is the affine or B-spline transform elastix computed), and
the log of elastix as it runs (it is not relayed by the WebAssembly pipeline).

The work is started and answered later. registerVolumes() takes an onFinished callback for that;
called without one, it waits - keeping the page drawing - where the code it runs in may be
suspended (a module self test, the Python console), and refuses where it may not (a button's slot).
"""

import logging
import os

logger = logging.getLogger("Elastix.web_launcher")


class RegistrationCancelled(Exception):
    """The registration was stopped by cancel() before it finished: what was asked for."""


def available():
    """Whether this application is a web page that can run work in a worker (SlicerWeb)."""
    try:
        from slicerweb import jobs
    except ImportError:
        return False
    return jobs.available()


def canWait():
    """Whether the code running now may be suspended until the worker answers, with the page
    drawing meanwhile (SlicerWeb's JavaScript Promise Integration, see slicerweb.yielding)."""
    try:
        from slicerweb import yielding
    except ImportError:
        return False
    return yielding.can_yield()


# What runs in the worker is ElastixLib.web_worker, a module of this extension, which the
# worker has as the page has it: every extension wheel is installed there too. Its main() is
# awaited, which only the worker's Python can do.
JOB_CODE = """
from ElastixLib import web_worker
result = await web_worker.main(argv)
"""


class WorkerLauncher:
    """Starts one registration in the worker and takes what it leaves in the nodes: the files it is
    given, the job, and the result read back when the worker answers."""

    def __init__(self, logic, fixedVolumeNode, movingVolumeNode, parameterFilenames, outputVolumeNode, outputTransformNode,
                 fixedVolumeMaskNode, movingVolumeMaskNode, initialTransformNode, onFinished):
        if fixedVolumeMaskNode is not None or movingVolumeMaskNode is not None:
            raise ValueError("Masks are not supported in a web browser: the elastix of ITK-Wasm takes none.")
        self.logic = logic
        self.fixedVolumeNode = fixedVolumeNode
        self.movingVolumeNode = movingVolumeNode
        self.parameterFilenames = list(parameterFilenames)
        self.outputVolumeNode = outputVolumeNode
        self.outputTransformNode = outputTransformNode
        self.initialTransformNode = initialTransformNode
        self.onFinished = onFinished
        self.error = None
        self.done = False
        self.directory = None
        self.paths = {}

    def start(self):
        import slicer
        from slicerweb import jobs

        self.directory = slicer.util.tempDirectory("Elastix")
        self.paths = {name: os.path.join(self.directory, name) for name in (
            "fixed.nrrd", "moving.nrrd", "initialTransform.tfm", "result.nrrd", "resultTransform.tfm", "resultParameters.json")}
        for index, filename in enumerate(self.parameterFilenames):
            self.paths[f"parameters.{index}.txt"] = filename
        paths = self.paths
        self.logic.addLog("Writing the volumes for elastix")
        slicer.util.exportNode(self.fixedVolumeNode, paths["fixed.nrrd"])
        slicer.util.exportNode(self.movingVolumeNode, paths["moving.nrrd"])
        if self.initialTransformNode is not None:
            # The transform from the parent, in LPS, as the desktop hands elastix its initial transform
            slicer.util.exportNode(self.initialTransformNode, paths["initialTransform.tfm"])
        # The worker is given the files that exist, and asked for the ones the run writes
        files = {}
        for path in paths.values():
            if os.path.isfile(path):
                with open(path, "rb") as handle:
                    files[path] = handle.read()
        arguments = {"fixed": paths["fixed.nrrd"], "moving": paths["moving.nrrd"], "result": paths["result.nrrd"],
                     "resultTransform": paths["resultTransform.tfm"], "resultParameters": paths["resultParameters.json"],
                     "parameterFiles": [paths[f"parameters.{index}.txt"] for index in range(len(self.parameterFilenames))],
                     "initialTransform": paths["initialTransform.tfm"] if self.initialTransformNode is not None else None}
        self.logic.addLog("Volume registration is started in a worker of the page (elastix in WebAssembly)")
        jobs.run(JOB_CODE, globals={"argv": arguments}, files=files,
                 outputs=[paths["result.nrrd"], paths["resultTransform.tfm"], paths["resultParameters.json"]],
                 onDone=self._onDone, onFailed=self._onFailed, onProgress=lambda message, fraction: self.logic.addLog(message))

    def cancel(self):
        from slicerweb import jobs

        self.error = RegistrationCancelled("Registration was cancelled.")
        jobs.cancel()

    def _onDone(self, result, files):
        import slicer

        try:
            for path, data in files.items():
                with open(path, "wb") as handle:
                    handle.write(data)
            self.logic.addLog("Registration computed: " + ", ".join(result.get("transforms", [])) + " transform")
            if self.outputVolumeNode is not None:
                self.logic._loadTransformedOutputVolume(self.outputVolumeNode, self.paths["result.nrrd"])
            if self.outputTransformNode is not None:
                self.logic.loadTransformFromFile(self.paths["resultTransform.tfm"], self.outputTransformNode)
                self.outputTransformNode.AddNodeReferenceID(slicer.vtkMRMLTransformNode.GetMovingNodeReferenceRole(), self.movingVolumeNode.GetID())
                self.outputTransformNode.AddNodeReferenceID(slicer.vtkMRMLTransformNode.GetFixedNodeReferenceRole(), self.fixedVolumeNode.GetID())
            self.logic.addLog("Registration is completed")
        except Exception as error:
            logger.exception("The registration result could not be read")
            self.error = error
        self._finish()

    def _onFailed(self, message):
        if self.error is None:
            self.error = RuntimeError(str(message))
        self.logic.addLog(str(self.error) if isinstance(self.error, RegistrationCancelled) else f"Registration failed: {message}")
        self._finish()

    def _finish(self):
        import shutil

        self.done = True
        if self.logic.deleteTemporaryFiles and self.directory:
            shutil.rmtree(self.directory, ignore_errors=True)
        self.logic.isRunning = False
        self.logic.cancelRequested = False
        self.logic.workerLauncher = None
        if self.onFinished is not None:
            self.onFinished(self.error)


def registerVolumes(logic, fixedVolumeNode, movingVolumeNode, parameterFilenames, outputVolumeNode, outputTransformNode,
                    fixedVolumeMaskNode, movingVolumeMaskNode, initialTransformNode, onFinished=None):
    """Register in the worker of the page; see this module's description for how it answers."""
    import time

    import slicer

    if onFinished is None and not canWait():
        raise RuntimeError("In a web browser the registration is computed in the background: call registerVolumes() with "
                           "an onFinished callback (or from code that may be suspended, such as a module test).")
    launcher = WorkerLauncher(logic, fixedVolumeNode, movingVolumeNode, parameterFilenames, outputVolumeNode, outputTransformNode,
                              fixedVolumeMaskNode, movingVolumeMaskNode, initialTransformNode, onFinished)
    logic.isRunning = True
    logic.cancelRequested = False
    logic.workerLauncher = launcher
    try:
        launcher.start()
    except Exception:
        logic.isRunning = False
        logic.workerLauncher = None
        raise
    if onFinished is not None:
        return
    while not launcher.done:
        slicer.app.processEvents()
        time.sleep(0.05)
    if launcher.error is not None:
        raise launcher.error
