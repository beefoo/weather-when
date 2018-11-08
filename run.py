# -*- coding: utf-8 -*-

import argparse
import datetime
import json
from lib import *
import numpy as np
import os
from PIL import Image, ImageOps, ImageDraw, ImageFont
from pprint import pprint
import subprocess
import sys

# input
parser = argparse.ArgumentParser()
# Data options
parser.add_argument('-date', dest="DATETIME", default="1986-01-29-18", help="Date to use; hours can be 00, 06, 12, or 18")
parser.add_argument('-forecast', dest="HOUR_FORECAST", default=6, type=int, help="Instantaneous forecast at x hours (x can be 0-6)")
parser.add_argument('-highres', dest="HIGH_RES", default=0, type=int, help="Download high res data? (takes much longer)")
# Image options
parser.add_argument('-width', dest="WIDTH", default=24, type=float, help="Width of image in inches")
parser.add_argument('-height', dest="HEIGHT", default=18, type=float, help="Height of image in inches")
parser.add_argument('-margin', dest="MARGIN", default=1, type=float, help="Margin in inches")
parser.add_argument('-dpi', dest="DPI", default=300, type=int, help="Dots per inch (resolution)")
parser.add_argument('-out', dest="OUTFILE", default="", help="Output filename")
# Wind style options
parser.add_argument('-lon', dest="LON_RANGE", default="0,360", help="Longitude range")
parser.add_argument('-ppp', dest="POINTS_PER_PARTICLE", type=int, default=1000, help="Points per particle")
parser.add_argument('-vel', dest="VELOCITY_MULTIPLIER", type=float, default=0.04, help="Number of pixels per degree of lon/lat")
parser.add_argument('-particles', dest="PARTICLES", type=int, default=100000, help="Number of particles to display")
parser.add_argument('-lw', dest="LINE_WIDTH_RANGE", default="1.0,1.0", help="Line width range")
parser.add_argument('-mag', dest="MAGNITUDE_RANGE", default="0.0,12.0", help="Magnitude range")
parser.add_argument('-alpha', dest="ALPHA_RANGE", default="0.0,200.0", help="Alpha range (0-255)")
# Label options
parser.add_argument('-label', dest="LABEL", default="", help="Label for image")
parser.add_argument('-font', dest="FONT", default="fonts/Bellefair-Regular.ttf", help="Font family")
parser.add_argument('-fsize', dest="FONT_SIZE", default=80, type=int, help="Font size in points")

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

DPI = args.DPI
WIDTH = args.WIDTH * DPI
HEIGHT = args.HEIGHT * DPI
MARGIN = args.MARGIN * DPI

LON_RANGE = [float(d) for d in args.LON_RANGE.strip().split(",")]
POINTS_PER_PARTICLE = args.POINTS_PER_PARTICLE
VELOCITY_MULTIPLIER = args.VELOCITY_MULTIPLIER
PARTICLES = args.PARTICLES
LINE_WIDTH_RANGE = tuple([float(v) for v in args.LINE_WIDTH_RANGE.split(",")])
MAGNITUDE_RANGE = tuple([float(v) for v in args.MAGNITUDE_RANGE.split(",")])
ALPHA_RANGE = tuple([float(v) for v in args.ALPHA_RANGE.split(",")])

LABEL = args.LABEL
if LABEL == "":
    dt = datetime.datetime.strptime("-".join([YYYY, MM, DD]), '%Y-%m-%d')
    LABEL = dt.strftime('Wind. %B %d, %Y')
FONT = args.FONT
FONT_SIZE = args.FONT_SIZE

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

# Initialize image data
windData = np.array(windData)
windData = windData.astype(np.float32)

# Offset the data
print "Offsetting data..."
offset = int(round(LON_RANGE[0] + 180.0))
if offset != 0.0:
    offset = int(round(offset / 360.0 * nx))
windData = offsetData(windData, nx, ny, offset)

# Initialize particle starting positions
particleProperties = [
    (pseudoRandom(i*3), # a stably random x
     pseudoRandom(i*3+1)) # a stably random y
    for i in range(PARTICLES)
]

# calculate content width and height
contentWidth = WIDTH - MARGIN*2
contentHeight = HEIGHT - MARGIN*2
contentX = MARGIN
contentY = MARGIN
targetRatio = 1.0 * contentWidth / contentHeight
dataRatio = 1.0 * nx / ny
# target is wider than data, adjust width
if targetRatio > dataRatio:
    oldWidth = contentWidth
    contentWidth = contentHeight * dataRatio
    contentX += (oldWidth-contentWidth) * 0.5
# target is narrower than data, adjust height
else:
    oldHeight = contentHeight
    contentHeight = contentWidth / dataRatio
    contentY += (oldHeight-contentHeight) * 0.5
contentWidth = roundInt(contentWidth)
contentHeight = roundInt(contentHeight)
contentX = roundInt(contentX)
contentY = roundInt(contentY)

print("Processing pixels...")
pixels = getPixelData(windData, nx, ny, contentWidth, contentHeight, particleProperties, POINTS_PER_PARTICLE, VELOCITY_MULTIPLIER, MAGNITUDE_RANGE, LINE_WIDTH_RANGE, ALPHA_RANGE)
print("Building image...")

# add pixels and invert
im = Image.fromarray(pixels, mode="L")
im = ImageOps.invert(im)

# add margin
base = Image.new('L', (WIDTH, HEIGHT), 255)
base.paste(im, (contentX, contentY, contentX+contentWidth, contentY+contentHeight))

# add label
labelMargin = roundInt(0.125 * DPI)
fnt = ImageFont.truetype(FONT, FONT_SIZE)
imgDraw = ImageDraw.Draw(base)
imgDraw.text((contentX, contentY + contentHeight + labelMargin), LABEL, font=fnt, fill=0)

print("Saving image...")
base.save(OUTFILE)
print("Saved file %s" % OUTFILE)
