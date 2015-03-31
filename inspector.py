#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# Interpreter version: python 2.7
#
# Imports =====================================================================
import os
import os.path
import sys
import ast
import imp


# Functions & classes =========================================================
def filter_private(tree):
    """Filter private AST elements."""
    return filter(lambda x: not x.name.startswith("_"), tree)


def get_func(tree):
    """Pick functions from AST `tree`."""
    out = []
    tree = filter(lambda x: isinstance(x, ast.FunctionDef), tree)

    for el in filter_private(tree):
        variables = map(lambda x: x.id, el.args.args)
        out.append("%s(%s)" % (el.name, ", ".join(variables)))

    return out


def get_classes(tree):
    """Pick classes from AST `tree`."""
    tree = filter(lambda x: isinstance(x, ast.ClassDef), tree)
    return map(lambda x: "class " + x.name, tree)


def get_properties(class_name, mod):
    """Pick properties which belongs to `class_name` in module `mod`."""
    out = []

    # look into module for given class_name
    cls = None
    try:
        cls = getattr(mod, class_name)
    except AttributeError:
        return []

    # well, this is useless, but you never know..
    if not cls:
        return []

    properties = []
    methods = []
    for el in dir(cls):
        if el.startswith("_"):
            continue

        obj = getattr(cls, el)

        if type(obj).__name__ == "method_descriptor":
            methods.append("." + obj.__name__ + "()")
        elif type(obj).__name__ == "property":
            properties.append("." + el)

    out.extend(properties)
    out.extend(methods)

    return out


def add_import_path(path):
    """
    Adds new import `path` to current path list.
    """
    if path not in sys.path:
        sys.path.insert(
            0,
            os.path.abspath(path)
        )


def import_module(filename, path):
    """
    Import `filename` as module.

    Args:
        filename (str): Local filename.
        path (str): Full path to the file.

    Returns:
        module obj: Imported module.
    """
    add_import_path(os.path.dirname(path))

    # try to import module, doesn't work for packages with relative imports
    try:
        return imp.load_source(filename, path)
    except ValueError:
        pass

    # handling of the 'ValueError: Attempted relative import in non-package'
    # problem
    import_path = os.path.dirname(os.path.dirname(path))
    package_name = os.path.basename(os.path.dirname(path))
    sub_package_name = os.path.splitext(os.path.basename(path))[0]

    add_import_path(import_path)
    return __import__(package_name + "." + sub_package_name)


def load_data_from_module(clsn, info_dict, path):
    """
    Get data for given element.
    """
    out = []
    filename = info_dict["filename"]

    # convert module path to file path
    full_path = os.path.join(path, filename)
    if not filename.endswith(".py"):
        full_path += ".py"

    # remove invisible unicode zero widht space character
    full_path = full_path.replace("_​_", "__")

    if not os.path.exists(full_path):
        sys.stderr.write("'%s' doesn't exists!\n" % full_path)
        return []

    if info_dict["type"] in ["module", "mod"]:
        mod = ast.parse(open(full_path).read()).body
        out.extend(get_func(mod))
        out.extend(get_classes(mod))
    elif info_dict["type"] in ["struct", "structure"]:
        out.extend(
            get_properties(
                clsn,
                import_module(filename, full_path)
            )
        )
    else:
        return []

    return out
