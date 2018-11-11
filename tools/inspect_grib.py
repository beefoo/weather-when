import numpy as np
from pprint import pprint
import pygrib
import sys


# grbs = pygrib.open('../downloads/gfsanl_4_20181026_1800_006.grb2')
# ugrb = grbs.select(name='10 metre U wind component')[0]
# vgrb = grbs.select(name='10 metre V wind component')[0]
#
# ny, nx = ugrb["values"].shape
# print("%s x %s = %s" % (nx, ny, nx*ny))
# data = ugrb['values'].reshape(-1)
# print(data[:20])
# sys.exit()

grbs = pygrib.open('../downloads/wnd10m.l.gdas.198601.grb2')
grbs = grbs.select(dataDate=19860101,stepRange='6',validityTime=1800)
print(len(grbs))
grbs = sorted(grbs, key=lambda d: d["parameterName"])

grb = grbs[0]

# keys = grb.keys()
# for key in keys:
#     print("%s=%s" % (key, grb[key]))

print(grb['values'].shape)
data = grb['values'].reshape(-1)
print(data[:20])
