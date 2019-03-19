# -*- coding: utf-8 -*-

import argparse
from datetime import datetime
from datetime import timedelta
from lib import *
import os
from pprint import pprint
import sys

# input
parser = argparse.ArgumentParser()
# Data options
parser.add_argument('-start', dest="DATETIME_START", default="2004-01-01-00", help="Date to use; hours can be 00, 06, 12, or 18")
parser.add_argument('-end', dest="DATETIME_END", default="2004-01-01-18", help="Date to use; hours can be 00, 06, 12, or 18")
parser.add_argument('-inc', dest="INCREMENT", default=6, type=int, help="Can be multiples of 6")
parser.add_argument('-highres', dest="HIGH_RES", default=1, type=int, help="Download high res data? (takes much longer)")
parser.add_argument('-rtmp', dest="REMOVE_TEMP", default=1, type=int, help="Remove temporary files?")
parser.add_argument('-outdir', dest="OUTPUT_DIR", default="output/", help="Output directory")
parser.add_argument('-dldir', dest="DOWNLOAD_DIR", default="downloads/", help="Download directory")
a = parser.parse_args()

DATE_FORMAT = "%Y-%m-%d-%H"

dateStart = datetime.strptime(a.DATETIME_START.strip(), DATE_FORMAT)
dateEnd = datetime.strptime(a.DATETIME_END.strip(), DATE_FORMAT)
dt = dateStart

while dt <= dateEnd:
    dateString = dt.strftime(DATE_FORMAT)
    yyyy, mm, dd, hh = tuple(dateString.split("-"))
    hour = int(hh)
    hourForecast = '0'
    # check if we need to use the forecast
    if hour % 6 > 0:
        hourForecast = '3'
        hour -= 3
        hh = str(hour).zfill(2)
    data = getData(a, yyyy, mm, dd, hh, hourForecast)
    # print("%s-%s-%s-%s %s" % (yyyy, mm, dd, hh, hourForecast))
    dt += timedelta(hours=a.INCREMENT)
