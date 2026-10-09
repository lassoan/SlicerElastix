"""The Insight transform file format (.tfm), the text form of an ITK transform::

    #Insight Transform File V1.0
    #Transform 0
    Transform: Euler3DTransform_double_3_3
    Parameters: 0.01 -0.02 0 6 -4 3
    FixedParameters: 1.5 -20 30

A transform is a dict here: {"type": "Euler3D", "dimension": 3, "parameters": [...],
"fixedParameters": [...]} - the type as itkwasm names it (its TransformParameterizations), without
the "Transform" suffix. A composite transform is a "Composite" entry followed by its components,
which ITK applies last first. Slicer reads the files this writes, as it reads the composite
transform file elastix writes on the desktop; nothing of Slicer or ITK is needed to write them.
"""

#: ITK's class names for the transform types, from itkwasm's names
ITK_CLASS_NAMES = {
    "Composite": "CompositeTransform", "Identity": "IdentityTransform", "Translation": "TranslationTransform",
    "Euler2D": "Euler2DTransform", "Euler3D": "Euler3DTransform", "Rigid2D": "Rigid2DTransform", "Rigid3D": "Rigid3DTransform",
    "VersorRigid3D": "VersorRigid3DTransform", "Versor": "VersorTransform", "Scale": "ScaleTransform",
    "Similarity2D": "Similarity2DTransform", "Similarity3D": "Similarity3DTransform", "Affine": "AffineTransform",
    "ScalableAffine": "ScalableAffineTransform", "BSpline": "BSplineTransform", "DisplacementField": "DisplacementFieldTransform",
}


def transform(kind, dimension, parameters=(), fixedParameters=()):
    """A transform record."""
    return {"type": kind, "dimension": dimension, "parameters": [float(v) for v in parameters],
            "fixedParameters": [float(v) for v in fixedParameters]}


def write(path, transforms):
    """Write transforms to an Insight transform file (double precision)."""
    lines = ["#Insight Transform File V1.0"]
    for index, item in enumerate(transforms):
        name = ITK_CLASS_NAMES.get(item["type"], item["type"] + "Transform")
        lines += [f"#Transform {index}", f"Transform: {name}_double_{item['dimension']}_{item['dimension']}",
                  "Parameters: " + " ".join(repr(float(v)) for v in item["parameters"]),
                  "FixedParameters: " + " ".join(repr(float(v)) for v in item["fixedParameters"])]
    with open(path, "w") as handle:
        handle.write("\n".join(lines) + "\n")


def read(path):
    """The transforms of an Insight transform file."""
    transforms = []
    with open(path) as handle:
        for line in handle:
            key, _, value = line.strip().partition(":")
            if key == "Transform":
                name, _, dimension, _ = value.strip().rsplit("_", 3)
                transforms.append(transform(name.replace("Transform", ""), int(dimension)))
            elif key in ("Parameters", "FixedParameters") and transforms:
                transforms[-1][key[0].lower() + key[1:]] = [float(v) for v in value.split()]
    return transforms
