#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# Interpreter version: python 2.7
#
# Imports =====================================================================
import urllib
import urllib2


# Functions & classes =========================================================
def to_png(uml):
    """
    Converts PlantUML source to png using plantuml.com demo server.
    """
    req = urllib2.Request(
        "http://www.plantuml.com/plantuml/form",
        urllib.urlencode({"text": uml})
    )

    data = urllib2.urlopen(req).read()

    # grab image url
    image_url = filter(
        lambda x: "http://www.plantuml.com:80/plantuml/png/" in x and
                  "<img" in x,
        data.splitlines()
    )[0]
    image_url = image_url.split(' src="')[1].split('"')[0]

    return urllib.urlopen(image_url).read()
