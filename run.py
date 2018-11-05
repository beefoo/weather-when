# -*- coding: utf-8 -*-

import argparse
import json
import numpy as np
import os
from pprint import pprint
import subprocess
import sys

# input
parser = argparse.ArgumentParser()
parser.add_argument('-date', dest="DATETIME", default="1986-01-29-18", help="Date to use; hours can be 00, 06, 12, or 18")
parser.add_argument('-forecast', dest="HOUR_FORECAST", default=6, type=int, help="Instantaneous forecast at x hours (x can be 0-6)")
parser.add_argument('-highres', dest="HIGH_RES", default=0, type=int, help="Download high res data? (takes much longer)")
parser.add_argument('-label', dest="LABEL", default="", help="Label for map")
parser.add_argument('-out', dest="OUTFILE", default="", help="Output filename")
args = parser.parse_args()

TEMP_DIR = "tmp/"
DOWNLOAD_DIR = "downloads/"
OUTPUT_DIR = "output/"

YYYY, MM, DD, HH = tuple(args.DATETIME.split("-"))
HOUR_FORECAST = args.HOUR_FORECAST

# example URL = https://nomads.ncdc.noaa.gov/data/cfsr/198601/wnd10m.l.gdas.198601.grb2.inv
prefix = "wnd10m.gdas" if args.HIGH_RES > 0 else "wnd10m.l.gdas"
filename = "%s.%s%s.grb2" % (prefix, YYYY, MM)
downloadURL = "https://nomads.ncdc.noaa.gov/data/cfsr/%s%s/%s" % (YYYY, MM, filename)

outFilename = ".".join([prefix, args.DATETIME, str(HOUR_FORECAST)])
dataPath = OUTPUT_DIR + outFilename +  ".json"
OUTFILE = OUTPUT_DIR + outFilename + ".png" if len(args.OUTFILE) <= 0 else args.OUTFILE

nx = None
ny = None
windData = []

# Check to see if we already processed this data
if not os.path.isfile(dataPath):

    # Attempt to download file .grib2 file
    gribPath = DOWNLOAD_DIR + filename
    if os.path.isfile(gribPath):
        print("%s already exists" % gribPath)
    else:
        print("Downloading %s..." % downloadURL)
        command = ['curl', '-o', gribPath, downloadURL]
        finished = subprocess.check_call(command)

    # Attempt to convert .grib2 file to .json
    # Via: https://github.com/weacast/weacast-grib2json
    jsonPath = TEMP_DIR + filename + ".json"
    if os.path.isfile(jsonPath):
        print("%s already exists" % jsonPath)
    else:
        print("Converting .grib2 to .json...")
        command = ['grib2json', '-d', '-n', '-o', jsonPath, gribPath]
        finished = subprocess.check_call(command)

    jsonData = {}
    print("Reading json data...")
    with open(jsonPath) as f:
        jsonData = json.load(f)

    # # misc debugging statements
    # def inspectJSON(data, key):
    #     labels = sorted(list(set([d["header"][key] for d in data])))
    #     pprint(labels)
    # print(len(jsonData))
    # inspectJSON(jsonData, "forecastTime")
    # inspectJSON(jsonData, "refTime")
    # pprint(jsonData[-1]["header"])
    # pprint(jsonData[0]["data"][:20])
    # sys.exit()

    # Filter to only the date/time and forecast hour of choice
    dateTimeString = "%s-%s-%sT%s:00:00.000Z" %  (YYYY, MM, DD, HH)
    jsonData = [d for d in jsonData if str(d["header"]["refTime"])==dateTimeString and d["header"]["forecastTime"]==HOUR_FORECAST]

    # We should have two results (one for U, one for V)
    if len(jsonData) != 2:
        print("Warning: data is invalid for this date/time/forecast. Found %s entries, expected 2" % len(jsonData))
    if len(jsonData) < 2:
        print("Exiting")
        sys.exit()

    # Sort results, so first entry is U and second is V
    jsonData = sorted(jsonData, key=lambda d: d["header"]["parameterNumberName"])
    nx = jsonData[0]["header"]["nx"]
    ny = jsonData[0]["header"]["ny"]
    print("%s x %s = %s" % (nx, ny, nx*ny))

    windData = np.zeros(nx * ny * 2)
    for i, vector in enumerate(jsonData):
        for j, value in enumerate(vector["data"]):
            index = j * 2 + i
            windData[index] = value

    dataOut = {
        "nx": nx,
        "ny": ny,
        "data": list(windData)
    }

    print("Writing processed data to file...")
    with open(dataPath, 'w') as f:
        json.dump(dataOut, f)
        print("Wrote processed data to %s" % dataPath)

    # delete temp files
    print("Deleting temporary files...")
    os.remove(gribPath)
    os.remove(jsonPath)

# We already processed data, just read it from file
else:
    processedData = {}
    print("Reading json data...")
    with open(dataPath) as f:
        processedData = json.load(f)

    nx = processedData["nx"]
    ny = processedData["ny"]
    windData = processedData["data"]
    print("%s x %s x 2 = %s" % (nx, ny, len(windData)))
