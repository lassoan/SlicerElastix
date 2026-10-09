"""Registration in the job worker of SlicerWeb: what ElastixLib.web_launcher starts there.

This runs in a Python of its own, the worker's, with the same packages as the page and without
the application: nothing of slicer or qt is imported here. The elastix of ITK-Wasm, the
itkwasm-elastix package, is awaited; the worker's Python can, the page's cannot. The files are
read and written with ITK-Wasm's image IO (itkwasm-image-io).

main(argv) takes the files of the run, which the page wrote and the worker was given:

- fixed, moving: the volumes (.nrrd)
- parameterFiles: the elastix parameter files, in order
- initialTransform: an Insight transform file (.tfm) with the initial transform, or None
- result, resultTransform, resultParameters: where to write the resampled moving volume (.nrrd),
  the transform (.tfm) and elastix's transform parameter maps (.json)

and returns what it made, as the job's result.
"""

import json
import os
import shlex

import numpy as np
import slicerweb_job as job
from itkwasm import FloatTypes, Transform, TransformType, cast_image
from itkwasm.pyodide import js_resources, to_js, to_py
from itkwasm_elastix_emscripten.js_package import js_package
from itkwasm_image_io_emscripten import nrrd_read_image_async, nrrd_write_image_async

from ElastixLib import web_itk_transform_io

# The pipelines run in this worker rather than in workers of their own
js_resources.web_worker = False


def read_parameter_file(path):
    """An elastix parameter file - lines of (Key value value ...), values quoted when text - as
    the parameter map of the parameter object: every value a string, as elastix keeps them.
    (itkwasm-elastix 2.1.0 has read_parameter_files_async for this, but it hands the pipeline
    the list of files as one file.)"""
    parameters = {}
    with open(path) as handle:
        for raw in handle:
            line = raw.split("//", 1)[0].strip()
            if line.startswith("(") and line.endswith(")"):
                tokens = shlex.split(line[1:-1])
                if tokens:
                    parameters[tokens[0]] = tokens[1:]
    return parameters


async def read_image(path):
    """A volume the page wrote, as the float image elastix registers."""
    could_read, image = await nrrd_read_image_async(_in_run_directory(path))
    if not could_read:
        raise RuntimeError(f"{path} could not be read as an image")
    return cast_image(image, component_type=FloatTypes.Float32)


async def write_image(image, path):
    """Write the resampled volume for the page, compressed as Slicer writes NRRD."""
    could_write, _ = await nrrd_write_image_async(image, _in_run_directory(path), use_compression=True)
    if not could_write:
        raise RuntimeError(f"{path} could not be written")


def _in_run_directory(path):
    """The file's name, with the run's directory made the current one: the IO pipelines keep a
    file system of their own with no directories in it, so a path with one fails to open."""
    os.chdir(os.path.dirname(path))
    return os.path.basename(path)


def itkwasm_transform(item):
    """A transform record (see web_itk_transform_io) as the itkwasm transform the pipeline takes."""
    kind = TransformType(transformParameterization=item["type"], parametersValueType="float64",
                         inputDimension=item["dimension"], outputDimension=item["dimension"])
    parameters = np.array(item["parameters"], np.float64)
    fixed = np.array(item["fixedParameters"], np.float64)
    return Transform(transformType=kind, numberOfFixedParameters=len(fixed), numberOfParameters=len(parameters),
                     fixedParameters=fixed, parameters=parameters)


def transforms_from_parameter_maps(maps, dimension, initial=()):
    """The transforms elastix computed, from its transform parameter maps (what its
    TransformParameters.<n>.txt files hold): one per registration stage, each composed with the
    ones before it, after the initial transforms if any. As ITK composes, the last of the list is
    applied first.

    (The pipeline also returns them as an ITK transform list, but that list's parameters arrive
    as references into the pipeline's memory, which the bridge does not read.)
    """
    stages = list(initial)
    for parameters in maps:
        kind = parameters["Transform"][0]
        values = parameters.get("TransformParameters", [])
        center = parameters.get("CenterOfRotationPoint", [0.0] * dimension)
        if kind == "TranslationTransform":
            stages.append(web_itk_transform_io.transform("Translation", dimension, values))
        elif kind in ("EulerTransform", "SimilarityTransform", "AffineTransform"):
            name = {"EulerTransform": f"Euler{dimension}D", "SimilarityTransform": f"Similarity{dimension}D", "AffineTransform": "Affine"}[kind]
            stages.append(web_itk_transform_io.transform(name, dimension, values, center))
        elif kind == "BSplineTransform":
            if parameters.get("BSplineTransformSplineOrder", ["3"])[0] != "3":
                raise RuntimeError("Only cubic B-spline transforms can be read in a web browser.")
            grid = [v for key in ("GridSize", "GridOrigin", "GridSpacing", "GridDirection") for v in parameters[key]]
            stages.append(web_itk_transform_io.transform("BSpline", dimension, values, grid))
        else:
            raise RuntimeError(f"The {kind} of elastix cannot be read as an ITK transform in a web browser.")
    if len(stages) == 1:
        return stages
    return [web_itk_transform_io.transform("Composite", dimension)] + stages[::-1]


async def main(argv):
    job.progress("Reading the volumes", 0.05)
    fixed = await read_image(argv["fixed"])
    moving = await read_image(argv["moving"])
    job.progress("Reading the parameter files", 0.1)
    parameter_object = [read_parameter_file(path) for path in argv["parameterFiles"]]
    initial = web_itk_transform_io.read(argv["initialTransform"]) if argv.get("initialTransform") else []
    # A file of ITK's holds a composite first and its components after it; the pipeline takes the components
    initial = [item for item in initial if item["type"] != "Composite"]
    options = {"initialTransform": to_js([itkwasm_transform(item) for item in initial])} if initial else {}

    job.progress("Registering (elastix in WebAssembly; this can take minutes)", 0.2)
    # The pipeline is called as itkwasm_elastix_emscripten.elastix_async calls it, but run in this
    # worker (webWorker=False) and with its outputs read here (see transforms_from_parameter_maps).
    js_module = await js_package.js_module
    outputs = await js_module.elastix(to_js(parameter_object), webWorker=False, noCopy=True, fixed=to_js(fixed), moving=to_js(moving), **options)
    outputs_map = outputs.as_object_map()
    result_image = to_py(outputs_map["result"])
    transform_parameters = outputs_map["transformParameterObject"].to_py()
    if not isinstance(transform_parameters, list):
        transform_parameters = [transform_parameters]
    transform_parameters = [dict(parameters) for parameters in transform_parameters]

    job.progress("Writing the result", 0.9)
    await write_image(result_image, argv["result"])
    transforms = transforms_from_parameter_maps(transform_parameters, 3, initial)
    web_itk_transform_io.write(argv["resultTransform"], transforms)
    with open(argv["resultParameters"], "w") as handle:
        json.dump(transform_parameters, handle, default=str, indent=1)
    return {"transforms": [item["type"] for item in transforms], "size": [int(s) for s in result_image.size]}
