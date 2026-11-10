"""Explicit software-fixture path seam; production Windows policy stays strict."""


def logical_local_path(value, roots, validate):
    if type(value) is str:
        normalized = value.replace("\\", "/")
        for root in roots:
            if root.startswith("/") and (normalized == root or normalized.startswith(root + "/")):
                return validate("C:" + normalized)
    return validate(value)
