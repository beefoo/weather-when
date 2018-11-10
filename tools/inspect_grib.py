import numpy as np
from pprint import pprint
import pygrib

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
