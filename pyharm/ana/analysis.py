
import numpy as np

from ..fluid_dump import FluidDump
from . import analyses

"""A bit like frame.py, this file exists mostly to offload code from the pyharm-analysis script.
"""

def write_ana_dict(out, out_full, n, n_dumps):
    """Write output of analyze() to a single HDF5 file.
    Note this is not thread-safe and must be called from one process
    """
    if out is None:
        print("Failed to read dump number {}".format(n))
        return
    for key in list(out.keys()):
        tag = key.split('/')[0]
        if key not in out_full:
            # Add destination ndarray of the right size if not present
            if tag == 't' or key == 'coord/t':
                out_full[key] = np.zeros(n_dumps)
            elif tag[-1:] == 't':
                # TODO make sure this still produces 1xN if n_dumps==1
                out_full[key] = np.zeros((n_dumps,)+out[key].shape)
            else:
                out_full[key] = np.zeros_like(out[key])

        # Slot in time-dependent vars, add averaged vars to running total
        try:
            if tag[-1:] == 't' or key == 'coord/t':
                out_full[key][n] = out[key]
            else:
                out_full[key][()] += out[key]
        except TypeError as e:
            print("Encountered error when updating {}: {}".format(key, e))

def analyze(args):
    fname, kwargs = args
    out = {}
    dump = FluidDump(fname)
    ana_types = kwargs['ana_types'].split(",")
    if "basic" not in ana_types:
        ana_types.append("basic")
    for type in ana_types:
        analyses.__dict__[type](dump, out, **kwargs)
    return out

def analyze_catch_err(args):
    try:
        return analyze(args)
    except:
        return None