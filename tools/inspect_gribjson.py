# -*- coding: utf-8 -*-

import json
from pprint import pprint

def inspectJSON(data, key):
    labels = sorted(list(set([d["header"][key] for d in data])))
    pprint(labels)

jsonData = {}
print("Reading json data...")
with open("../tmp/wnd10m.l.gdas.198601.json") as f:
    jsonData = json.load(f)

# misc debugging statements
print(len(jsonData))
# inspectJSON(jsonData, "forecastTime")
# inspectJSON(jsonData, "refTime")
pprint(jsonData[-1]["header"])
pprint(jsonData[0]["data"][:20])
