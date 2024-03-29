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
#  python run.py -size fill -width 11 -height 8.5 -margin 0.5 -label "" -lw " 1.0,1.0"

# input
parser = argparse.ArgumentParser()
# Data options
parser.add_argument('-date', dest="DATETIME", default="1986-01-29-18", help="Date to use; hours can be 00, 06, 12, or 18")
parser.add_argument('-forecast', dest="HOUR_FORECAST", default='0', help="Instantaneous forecast at x hours (x can be 0, 3, or 6)")
parser.add_argument('-highres', dest="HIGH_RES", default=1, type=int, help="Download high res data? (takes much longer)")
parser.add_argument('-rtmp', dest="REMOVE_TEMP", default=1, type=int, help="Remove temporary files?")
parser.add_argument('-outdir', dest="OUTPUT_DIR", default="output/", help="Output directory")
parser.add_argument('-dldir', dest="DOWNLOAD_DIR", default="downloads/", help="Download directory")
# Image options
parser.add_argument('-width', dest="WIDTH", default=20, type=float, help="Width of image in inches")
parser.add_argument('-height', dest="HEIGHT", default=16, type=float, help="Height of image in inches")
parser.add_argument('-margin', dest="MARGIN", default=1, type=float, help="Margin in inches")
parser.add_argument('-dpi', dest="DPI", default=300, type=int, help="Dots per inch (resolution)")
parser.add_argument('-out', dest="OUTFILE", default="", help="Output filename")
parser.add_argument('-size', dest="RESIZE_TYPE", default="fit", help="Fit or fill")
parser.add_argument('-offsetx', dest="OFFSETX", default=0.0, type=float, help="X offset in inches")
parser.add_argument('-offsety', dest="OFFSETY", default=0.0, type=float, help="Y offset in inches")
# Wind style options
parser.add_argument('-lon', dest="LON_RANGE", default="0,360", help="Longitude range")
parser.add_argument('-ppp', dest="POINTS_PER_PARTICLE", type=int, default=1000, help="Points per particle; higher values means longer lines")
parser.add_argument('-vel', dest="VELOCITY_MULTIPLIER", type=float, default=0.04, help="Number of pixels per degree of lon/lat; smaller values create more detailed curves")
parser.add_argument('-particles', dest="PARTICLES", type=int, default=150000, help="Number of particles to display")
parser.add_argument('-lw', dest="LINE_WIDTH_RANGE", default="2.0,2.0", help="Line width range")
parser.add_argument('-mag', dest="MAGNITUDE_RANGE", default="0.0,12.0", help="Magnitude range")
parser.add_argument('-alpha', dest="ALPHA_RANGE", default="0.0,255.0", help="Alpha range (0-255)")
parser.add_argument('-blur', dest="BLUR_RADIUS", default=0.0, type=float, help="Blur radius")
parser.add_argument('-brightness', dest="BRIGHTNESS", default=0.3, type=float, help="Brightness factor; should be 0.0 < x < 1.0; 1.0 = no change")
parser.add_argument('-layers', dest="LAYERS", default=10, type=int, help="Number of layers to composite (more = darker)")
# Label options
parser.add_argument('-label', dest="LABEL", default="auto", help="Label for image")
parser.add_argument('-font', dest="FONT", default="fonts/Bellefair-Regular.ttf", help="Font family")
parser.add_argument('-fsize', dest="FONT_SIZE", default=40, type=int, help="Font size in points")

args = parser.parse_args()

DOWNLOAD_DIR = args.DOWNLOAD_DIR
OUTPUT_DIR = args.OUTPUT_DIR

YYYY, MM, DD, HH = tuple(args.DATETIME.strip().split("-"))
HOUR_FORECAST = args.HOUR_FORECAST

# Dates: Jan 1, 1979 - Mar 31, 2011
    # Source: https://www.ncdc.noaa.gov/data-access/model-data/model-datasets/climate-forecast-system-version2-cfsv2#CFS%20Reanalysis%20(CFSR)
    # Old URL = https://nomads.ncdc.noaa.gov/data/cfsr/198601/wnd10m.l.gdas.198601.grb2
    # New URL = https://www.ncei.noaa.gov/data/climate-forecast-system/access/reanalysis/time-series/198601/wnd10m.l.gdas.198601.grb2
# Dates: Apr 1, 2011 - 6 months ago
    # Source: https://www.ncdc.noaa.gov/data-access/model-data/model-datasets/climate-forecast-system-version2-cfsv2#CFSv2%20Operational%20Analysis
    # Old URL = https://nomads.ncdc.noaa.gov/modeldata/cfsv2_analysis_timeseries/2011/201104/wnd10m.l.gdas.201104.grib2
    # New URL = https://www.ncei.noaa.gov/data/climate-forecast-system/access/operational-analysis/time-series/2011/201104/wnd10m.l.gdas.201104.grib2
# Dates: 6 months ago - ~3days ago
    # Source: https://www.ncdc.noaa.gov/data-access/model-data/model-datasets/global-forcast-system-gfs
    # Example URL = https://nomads.ncdc.noaa.gov/data/gfsanl/201810/20181026/gfsanl_4_20181026_1800_006.grb2

downloadURL, filename, outFilename, requestedDate, isForecast = getDownloadData(args, YYYY, MM, DD, HH, HOUR_FORECAST)

OUTFILE = args.OUTFILE.strip()
if OUTFILE.startswith("+"):
    OUTFILE = OUTPUT_DIR + outFilename + OUTFILE[1:] + ".png"
elif len(OUTFILE) <= 0:
    OUTFILE = OUTPUT_DIR + outFilename + ".png"

DPI = args.DPI
WIDTH = args.WIDTH * DPI
HEIGHT = args.HEIGHT * DPI
MARGIN = args.MARGIN * DPI
RESIZE_TYPE = args.RESIZE_TYPE
OFFSETX = args.OFFSETX * DPI
OFFSETY = args.OFFSETY * DPI

LON_RANGE = [float(d) for d in args.LON_RANGE.strip().split(",")]
POINTS_PER_PARTICLE = args.POINTS_PER_PARTICLE
VELOCITY_MULTIPLIER = args.VELOCITY_MULTIPLIER
PARTICLES = args.PARTICLES
LINE_WIDTH_RANGE = tuple([float(v) for v in args.LINE_WIDTH_RANGE.strip().split(",")])
MAGNITUDE_RANGE = tuple([float(v) for v in args.MAGNITUDE_RANGE.strip().split(",")])
ALPHA_RANGE = tuple([float(v) for v in args.ALPHA_RANGE.strip().split(",")])
BLUR_RADIUS = args.BLUR_RADIUS
BRIGHTNESS = args.BRIGHTNESS
LAYERS = args.LAYERS
PARTICLES_PER_LAYER = PARTICLES / LAYERS
SMOOTH_FACTOR = 2.0

LABEL = args.LABEL.strip()
defaultLabel = requestedDate.strftime('Wind at 10m above sea level on %B %d, %Y')
if LABEL.startswith("+"):
    LABEL = defaultLabel + LABEL[1:]
elif LABEL == "auto":
    LABEL = defaultLabel
FONT = args.FONT
FONT_SIZE = args.FONT_SIZE

windData = getData(args, YYYY, MM, DD, HH, HOUR_FORECAST)

# Initialize image data
ny, nx, _ = windData.shape
windData = windData.reshape(-1)
windData = windData.astype(np.float32)

# Offset the data
print("Offsetting data...")
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
cropToWidth = None
cropToHeight = None

# fill the content area
if RESIZE_TYPE == "fill":
    cropToWidth = contentWidth
    cropToHeight = contentHeight

    # target is wider than data, adjust height
    if targetRatio > dataRatio:
        contentHeight = contentWidth / dataRatio

    # target is narrower than data, adjust width
    else:
        contentWidth = contentHeight * dataRatio

# else, resize to fit
else:
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
if LAYERS > 1:
    pixelLayers = np.zeros((scaledH, scaledW, LAYERS), dtype=np.uint8)
    for l in range(LAYERS):
        l0 = PARTICLES_PER_LAYER * l
        l1 = min(PARTICLES_PER_LAYER * (l+1), PARTICLES)
        pixelLayer = getPixelData(windData, nx, ny, scaledW, scaledH, particleProperties[l0:l1], POINTS_PER_PARTICLE, VELOCITY_MULTIPLIER, MAGNITUDE_RANGE, LINE_WIDTH_RANGE, ALPHA_RANGE, BRIGHTNESS)
        pixelLayers[:,:,l] = pixelLayer
        sys.stdout.write('\r')
        sys.stdout.write("%s%%" % round(1.0*(l+1)/LAYERS*100,1))
        sys.stdout.flush()
    pixels = np.amax(pixelLayers, axis=2)
else:
    pixels = getPixelData(windData, nx, ny, scaledW, scaledH, particleProperties, POINTS_PER_PARTICLE, VELOCITY_MULTIPLIER, MAGNITUDE_RANGE, LINE_WIDTH_RANGE, ALPHA_RANGE, BRIGHTNESS)
print("Building image...")

# add pixels and invert
im = Image.fromarray(pixels, mode="L")
im = ImageOps.invert(im)
if SMOOTH_FACTOR > 0.0:
    im = im.resize((contentWidth, contentHeight), Image.LANCZOS)
if BLUR_RADIUS > 0:
    im = im.filter(ImageFilter.GaussianBlur(BLUR_RADIUS))

# crop if necessary
if cropToWidth and cropToHeight:
    im = im.crop((roundInt(OFFSETX), roundInt(OFFSETY), roundInt(OFFSETX+cropToWidth), roundInt(OFFSETY+cropToHeight)))

# add margin
base = Image.new('L', (roundInt(WIDTH), roundInt(HEIGHT)), 255)
cw, ch = im.size
base.paste(im, (contentX, contentY, contentX+cw, contentY+ch))

# add label
if len(LABEL) > 0:
    labelMargin = roundInt(0.125 * DPI)
    fnt = ImageFont.truetype(FONT, FONT_SIZE)
    imgDraw = ImageDraw.Draw(base)
    imgDraw.text((contentX, contentY + contentHeight + labelMargin), LABEL, font=fnt, fill=0)

print("Saving image...")
base.save(OUTFILE, dpi=(DPI, DPI))
print("Saved file %s" % OUTFILE)
