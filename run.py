# -*- coding: utf-8 -*-

import argparse
from datetime import datetime
from datetime import timedelta
import json
from lib import *
import numpy as np
import os
from PIL import Image, ImageOps, ImageDraw, ImageFont, ImageFilter
from pprint import pprint
import subprocess
import sys

#  python run.py
#  python run.py -lw " 1.0,1.0"
#  python run.py -alpha " 0.0,255.0"
#  python run.py -lw " 1.0,1.0" -brightness 0.5 -alpha " 0.0,255.0"
#  python run.py -date " 2012-10-29-18" -out " +_sandy" -label " +, Hurricane Sandy"
#  python run.py -date " 2017-08-26-18" -out " +_harvey" -label " +, Hurricane Harvey"

# input
parser = argparse.ArgumentParser()
# Data options
parser.add_argument('-date', dest="DATETIME", default="1986-01-29-18", help="Date to use; hours can be 00, 06, 12, or 18")
parser.add_argument('-forecast', dest="HOUR_FORECAST", default='6', help="Instantaneous forecast at x hours (x can be 0, 3, or 6)")
parser.add_argument('-highres', dest="HIGH_RES", default=1, type=int, help="Download high res data? (takes much longer)")
parser.add_argument('-rtmp', dest="REMOVE_TEMP", default=1, type=int, help="Remove temporary files?")
# Image options
parser.add_argument('-width', dest="WIDTH", default=20, type=float, help="Width of image in inches")
parser.add_argument('-height', dest="HEIGHT", default=16, type=float, help="Height of image in inches")
parser.add_argument('-margin', dest="MARGIN", default=3, type=float, help="Margin in inches")
parser.add_argument('-dpi', dest="DPI", default=300, type=int, help="Dots per inch (resolution)")
parser.add_argument('-out', dest="OUTFILE", default="", help="Output filename")
# Wind style options
parser.add_argument('-lon', dest="LON_RANGE", default="0,360", help="Longitude range")
parser.add_argument('-ppp', dest="POINTS_PER_PARTICLE", type=int, default=1000, help="Points per particle; higher values means longer lines")
parser.add_argument('-vel', dest="VELOCITY_MULTIPLIER", type=float, default=0.04, help="Number of pixels per degree of lon/lat; smaller values create more detailed curves")
parser.add_argument('-particles', dest="PARTICLES", type=int, default=150000, help="Number of particles to display")
parser.add_argument('-lw', dest="LINE_WIDTH_RANGE", default="2.0,2.0", help="Line width range")
parser.add_argument('-mag', dest="MAGNITUDE_RANGE", default="0.0,12.0", help="Magnitude range")
parser.add_argument('-alpha', dest="ALPHA_RANGE", default="0.0,255.0", help="Alpha range (0-255)")
parser.add_argument('-blur', dest="BLUR_RADIUS", default=0.0, type=float, help="Blur radius")
parser.add_argument('-brightness', dest="BRIGHTNESS", default=0.2, type=float, help="Brightness factor; should be 0.0 < x < 1.0; 1.0 = no change")
# Label options
parser.add_argument('-label', dest="LABEL", default="", help="Label for image")
parser.add_argument('-font', dest="FONT", default="fonts/Bellefair-Regular.ttf", help="Font family")
parser.add_argument('-fsize', dest="FONT_SIZE", default=40, type=int, help="Font size in points")

args = parser.parse_args()

DOWNLOAD_DIR = "downloads/"
OUTPUT_DIR = "output/"

YYYY, MM, DD, HH = tuple(args.DATETIME.strip().split("-"))
HOUR_FORECAST = args.HOUR_FORECAST

# Dates: Jan 1, 1979 - Mar 31, 2011
    # Source: https://www.ncdc.noaa.gov/data-access/model-data/model-datasets/climate-forecast-system-version2-cfsv2#CFS%20Reanalysis%20(CFSR)
    # Example URL = https://nomads.ncdc.noaa.gov/data/cfsr/198601/wnd10m.l.gdas.198601.grb2
# Dates: Apr 1, 2011 - 6 months ago
    # Source: https://www.ncdc.noaa.gov/data-access/model-data/model-datasets/climate-forecast-system-version2-cfsv2#CFSv2%20Operational%20Analysis
    # Example URL = https://nomads.ncdc.noaa.gov/modeldata/cfsv2_analysis_timeseries/2011/201104/wnd10m.l.gdas.201104.grib2
# Dates: 6 months ago - ~3days ago
    # Source: https://www.ncdc.noaa.gov/data-access/model-data/model-datasets/global-forcast-system-gfs
    # Example URL = https://nomads.ncdc.noaa.gov/data/gfsanl/201810/20181026/gfsanl_4_20181026_1800_006.grb2

prefix = "wnd10m.gdas" if args.HIGH_RES > 0 else "wnd10m.l.gdas"
filename = "%s.%s%s.grb2" % (prefix, YYYY, MM)
downloadURL = "https://nomads.ncdc.noaa.gov/data/cfsr/%s%s/%s" % (YYYY, MM, filename)
now = datetime.now()
sixMonthsAgo = now - timedelta(6*30)
requestedDate = datetime.strptime("-".join([YYYY, MM, DD]), '%Y-%m-%d')
isForecast = requestedDate > sixMonthsAgo
outFilename = ".".join([prefix, args.DATETIME.strip(), HOUR_FORECAST])

if isForecast:
    filename = "gfsanl_4_%s%s%s_%s00_00%s.grb2" % (YYYY, MM, DD, HH, HOUR_FORECAST)
    downloadURL = "https://nomads.ncdc.noaa.gov/data/gfsanl/%s%s/%s%s%s/%s" % (YYYY, MM, YYYY, MM, DD, filename)
    outFilename = filename
elif int(YYYY) > 2011 or int(YYYY) == 2011 and int(MM) >= 4:
    filename = "%s.%s%s.grib2" % (prefix, YYYY, MM)
    downloadURL = "https://nomads.ncdc.noaa.gov/modeldata/cfsv2_analysis_timeseries/%s/%s%s/%s" % (YYYY, YYYY, MM, filename)

dataPath = OUTPUT_DIR + outFilename +  ".json"
OUTFILE = args.OUTFILE.strip()
if OUTFILE.startswith("+"):
    OUTFILE = OUTPUT_DIR + outFilename + OUTFILE[1:] + ".png"
elif len(OUTFILE) <= 0:
    OUTFILE = OUTPUT_DIR + outFilename + ".png"
REMOVE_TEMP = args.REMOVE_TEMP > 0

DPI = args.DPI
WIDTH = args.WIDTH * DPI
HEIGHT = args.HEIGHT * DPI
MARGIN = args.MARGIN * DPI

LON_RANGE = [float(d) for d in args.LON_RANGE.strip().split(",")]
POINTS_PER_PARTICLE = args.POINTS_PER_PARTICLE
VELOCITY_MULTIPLIER = args.VELOCITY_MULTIPLIER
PARTICLES = args.PARTICLES
LINE_WIDTH_RANGE = tuple([float(v) for v in args.LINE_WIDTH_RANGE.strip().split(",")])
MAGNITUDE_RANGE = tuple([float(v) for v in args.MAGNITUDE_RANGE.strip().split(",")])
ALPHA_RANGE = tuple([float(v) for v in args.ALPHA_RANGE.strip().split(",")])
BLUR_RADIUS = args.BLUR_RADIUS
BRIGHTNESS = args.BRIGHTNESS
SMOOTH_FACTOR = 2.0

LABEL = args.LABEL.strip()
defaultLabel = requestedDate.strftime('Wind at 10m above sea level on %B %d, %Y')
if LABEL.startswith("+"):
    LABEL = defaultLabel + LABEL[1:]
elif LABEL == "":
    LABEL = defaultLabel
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

    print("Reading GRIB file...")
    import pygrib
    grbs = pygrib.open(gribPath)

    if isForecast:
        ugrb = grbs.select(name='10 metre U wind component')[0]
        vgrb = grbs.select(name='10 metre V wind component')[0]
        grbs = [ugrb, vgrb]
    else:
        dataDate = int(YYYY+MM+DD)
        validityTime = int(HH) * 100
        grbs = grbs.select(dataDate=dataDate,stepRange=HOUR_FORECAST,validityTime=validityTime)
        # Sort results, so first entry is U and second is V
        grbs = sorted(grbs, key=lambda d: d["parameterName"])

    # We should have two results (one for U, one for V)
    if len(grbs) != 2:
        print("Warning: data is invalid for this date/time/forecast. Found %s entries, expected 2" % len(jsonData))
    if len(grbs) < 2:
        print("Exiting")
        sys.exit()

    first = grbs[0]
    ny, nx = grbs[0]["values"].shape
    print("%s x %s = %s" % (nx, ny, nx*ny))

    windData = np.zeros(nx * ny * 2)
    for i, vector in enumerate(grbs):
        data = vector['values'].reshape(-1)
        for j, value in enumerate(data):
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
    if REMOVE_TEMP:
        print("Deleting temporary files...")
        os.remove(gribPath)

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
scaledW = roundInt(contentWidth * SMOOTH_FACTOR)
scaledH = roundInt(contentHeight * SMOOTH_FACTOR)
pixels = getPixelData(windData, nx, ny, scaledW, scaledH, particleProperties, POINTS_PER_PARTICLE, VELOCITY_MULTIPLIER, MAGNITUDE_RANGE, LINE_WIDTH_RANGE, ALPHA_RANGE, BRIGHTNESS)
print("Building image...")

# add pixels and invert
im = Image.fromarray(pixels, mode="L")
im = ImageOps.invert(im)
if SMOOTH_FACTOR > 0.0:
    im = im.resize((contentWidth, contentHeight), Image.LANCZOS)
if BLUR_RADIUS > 0:
    im = im.filter(ImageFilter.GaussianBlur(BLUR_RADIUS))

# add margin
base = Image.new('L', (WIDTH, HEIGHT), 255)
base.paste(im, (contentX, contentY, contentX+contentWidth, contentY+contentHeight))

# add label
labelMargin = roundInt(0.125 * DPI)
fnt = ImageFont.truetype(FONT, FONT_SIZE)
imgDraw = ImageDraw.Draw(base)
imgDraw.text((contentX, contentY + contentHeight + labelMargin), LABEL, font=fnt, fill=0)

print("Saving image...")
base.save(OUTFILE, dpi=(DPI, DPI))
print("Saved file %s" % OUTFILE)
