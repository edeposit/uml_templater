#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# Interpreter version: python 2.7
#
# Imports =====================================================================
import os
import sys
import ast
import imp
import os.path
import argparse
import urllib
import urllib2


# Variables ===================================================================
# Functions & objects =========================================================
def _add_import_path(path):
    """
    Adds new import `path` to current path list.
    """
    if path not in sys.path:
        sys.path.insert(
            0,
            os.path.abspath(path)
        )


def _get_png(uml):
    """
    Converts PlantUML source to gif using plantuml.com demo server.
    """
    req = urllib2.Request(
        "http://www.plantuml.com/plantuml/form",
        urllib.urlencode({"text": uml})
    )

    data = urllib2.urlopen(req).read()

    image = filter(
        lambda x: "http://www.plantuml.com:80/plantuml/png/" in x and
                  "<img" in x,
        data.splitlines()
    )[0]
    image = image.split(' src="')[1].split('"')[0]

    return urllib.urlopen(image).read()


def _get_class_name(line):
    line = line.split("class")[1]
    line = line.split("{")[0]
    line = line.strip()

    if '"' or "'" in line:
        line = line.split("'") if "'" in line else line.split('"')
        line = filter(lambda x: x.strip(), line)
        line = line[0]

    return line.strip().split()[0]


def _get_data(clsn, info_dict, path):
    """
    Get data for given element.
    """
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

    out = []

    # convert module path to file path
    fn = path + "/" + info_dict["fn"]
    if not info_dict["fn"].endswith(".py"):
        fn += ".py"

    fn = fn.replace("_​_", "__")

    if not os.path.exists(fn):
        sys.stderr.write("'%s' doesn't exists!\n" % fn)
        return []

    if info_dict["type"] in ["module", "mod"]:
        mod = ast.parse(open(fn).read()).body
        out.extend(get_func(mod))
        out.extend(get_classes(mod))
    elif info_dict["type"] in ["struct", "structure"]:
        _add_import_path(os.path.dirname(fn))
        mod = imp.load_source(info_dict["fn"], fn)
        out.extend(get_properties(clsn, mod))
    else:
        return []

    return out


def process_uml_file(filename, path):
    data = None
    with open(filename) as f:
        data = f.read()

    out = []
    class_stack = []
    class_info = {}
    for line in data.splitlines():
        if line.strip().startswith("class"):
            clsn = _get_class_name(line)
            class_stack.append(clsn)
            class_info[clsn] = {
                "spacer": line.split("class")[0] + "    "
            } 

        # user configuration in form ala $templater:struct:structures
        if class_stack and line.strip().startswith("$templater"):
            parsed = line.strip().split(":")
            class_info[class_stack[-1]]["type"] = parsed[1]
            class_info[class_stack[-1]]["fn"] = parsed[2]
            continue

        if "}" in line and class_stack:
            clsn = class_stack.pop()

            # spacer is in class_info everytime, but rest is not
            if clsn in class_info and len(class_info[clsn].items()) > 1:
                data = _get_data(clsn, class_info[clsn], path)

                # apply spacer
                data = map(lambda x: class_info[clsn]["spacer"] + x, data)

                out.extend(data)
                del class_info[clsn]

        out.append(line)

    uml = "\n".join(out)
    new_filename = filename.replace("template_", "")

    # write new uml to new file
    with open(new_filename, "w") as f:
        f.write(uml)

    # create image
    with open(new_filename.rsplit(".", 1)[0] + ".png", "wb") as f:
        f.write(_get_png(uml))

    return new_filename


# Main program ================================================================
if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="""PlantUML method filler.
                       This script expects directory with template_* named
                       PlantUML files, which are converted to png.
                       $templater:type:modulename is replaced by content of
                       modulename. Type can be 'struct' or 'module'.""")
    parser.add_argument(
        "-i",
        "--ipath",
        type=str,
        metavar="IMPORT_PATH",
        required=True,
        help="Import path to your project."
    )
    parser.add_argument(
        "static_dir",
        type=str,
        metavar="STATIC_DIR",
        help="Path to the _static directory for sphinx."
    )
    args = parser.parse_args()

    _add_import_path(args.ipath)

    for filename in os.listdir(args.static_dir):
        filename = args.static_dir + "/" + filename
        if not os.path.isfile(filename):
            continue

        if not os.path.basename(filename).startswith("template_"):
            continue

        print filename, "-->", process_uml_file(filename, args.ipath)
