import numpy as np
from pprint import pprint
import pyopencl as cl

def inspectJSON(data, key):
    labels = sorted(list(set([d["header"][key] for d in data])))
    pprint(labels)
