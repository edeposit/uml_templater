#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# Interpreter version: python 2.7
#
# Imports =====================================================================
from __future__ import absolute_import

import os
import os.path
import argparse


import plantuml
import inspector


# Functions & objects =========================================================
def parse_class_name(line):
    line = line.split("class")[1]
    line = line.split("{")[0]
    line = line.strip()

    if '"' or "'" in line:
        line = line.split("'") if "'" in line else line.split('"')
        line = filter(lambda x: x.strip(), line)
        line = line[0]

    return line.strip().split()[0]


def process_uml_file(filename, path):
    data = None
    with open(filename) as f:
        data = f.read()

    out = []
    class_info = {}
    class_stack = []
    for line in data.splitlines():
        if line.strip().startswith("class"):
            clsn = parse_class_name(line)
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
                data = inspector.load_data_from_module(
                    clsn,
                    class_info[clsn],
                    path
                )

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
        f.write(plantuml.to_png(uml))

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

    inspector.add_import_path(args.ipath)

    for filename in os.listdir(args.static_dir):
        filename = args.static_dir + "/" + filename
        if not os.path.isfile(filename):
            continue

        if not os.path.basename(filename).startswith("template_"):
            continue

        print filename, "-->", process_uml_file(filename, args.ipath)
