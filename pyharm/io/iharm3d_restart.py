import h5py
import numpy as np

from pyharm.io.iharm3d import Iharm3DFile

from .. import parameters
from .interface import DumpFile
from .iharm3d import Iharm3DFile
from .iharm3d_header import _write_value

def write_restart(dump, fname, astype=np.float64):
    with h5py.File(fname, "w") as outf:

        # Record this was converted
        _write_value(outf, "pyharm-converter-0.1", 'version')
        # Variables needed for restarting
        outf['n1'] = dump['n1']
        outf['n2'] = dump['n2']
        outf['n3'] = dump['n3']
        outf['gam'] = dump['gam']
        outf['cour'] = dump['cour']
        outf['t'] = dump['t']
        outf['dt'] = dump['dt']
        if 'tf' in dump.params:
            outf['tf'] = dump['tf']
        elif 'tlim' in dump.params:
            outf['tf'] = dump['tlim']
        if 'a' in dump.params:
            outf['a'] = dump['a']
            outf['hslope'] = dump['hslope']
            outf['Rhor'] = dump['r_eh']
            outf['Rin'] = dump['r_in']
            outf['Rout'] = dump['r_out']
            outf['R0'] = 0.0
        else:
            outf['x1Min'] = dump['x1min']
            outf['x1Max'] = dump['x1max']
            outf['x2Min'] = dump['x2min']
            outf['x2Max'] = dump['x2max']
            outf['x3Min'] = dump['x3min']
            outf['x3Max'] = dump['x3max']
        if 'n_step' in dump.params:
            outf['nstep'] = dump['n_step']
        if 'n_dump' in dump.params:
            outf['dump_cnt'] = dump['n_dump']
        if 'game' in dump.params:
            outf['game'] = dump['game']
            outf['gamp'] = dump['gamp']
            # This one seems unnecessary?
            outf['fel0'] = dump['fel0']

        # Every KHARMA dump is full
        outf['DTd'] = dump['dump_cadence']
        outf['DTf'] = dump['dump_cadence']
        # These isn't recorded from KHARMA
        outf['DTl'] = 0.1
        outf['DTp'] = 100
        outf['DTr'] = 10000
        # I dunno what this is
        outf['restart_id'] = 100
        
        if 'next_dump_time' in dump.params:
            outf['tdump'] = dump['next_dump_time']
        else:
            outf['tdump'] = dump['t'] + dump['dump_cadence']
        if 'next_log_time' in dump.params:
            outf['tlog'] = dump['next_log_time']
        else:
            outf['tlog'] = dump['t'] + 0.1

        # This will fetch and write all primitive variables,
        # sans ghost zones as is customary for iharm3d restart files
        G = dump.grid
        if G.NG > 0:
            p = dump.reader.read_var('prims', astype=astype)
            outf["p"] = np.einsum("pijk->pkji", p[G.slices.allv + G.slices.bulk]).astype(astype)
        else:
            p = dump.reader.read_var('prims', astype=astype)
            outf["p"] = np.einsum("pijk->pkji", p).astype(astype)

class Iharm3DRestart(Iharm3DFile):
    """File filter class for iharm3d restart files. Overrides just parameters & read_var methods.
    """

    def read_params(self, **kwargs):
        """Read the file header and per-dump parameters (t, dt, etc)"""
        with h5py.File(self.fname, "r") as fil:
            params = {}
            # Add everything a restart file records
            for key in ['DTd', 'DTf', 'DTl', 'DTp', 'DTr', 'cour', 'dt', 'dump_cnt',
                        'gam', 'n1', 'n2', 'n3', 'nstep', 'restart_id', 't', 'tdump',
                        'tf', 'tlog', 'version']:
                if key in fil:
                    params[key] = fil[key][()]
            if 'a' in fil.keys():
                for key in ['a', 'hslope', 'R0', 'Rhor', 'Rin', 'Rout']:
                    if key in fil:
                        params[key] = fil[key][()]
                params['coordinates'] = 'fmks'
            # TODO ELSE CARTESIAN

            return parameters.fix(params)

    def read_var(self, var, slc=(), **kwargs):
        if var in self.cache:
            return self.cache[var]
        with h5py.File(self.fname, "r") as fil:
            # Translate the slice to a portion of the file
            # A bit overkill to stay adaptable: keeps all dimensions until squeeze in _prep_array
            # TODO ghost zones
            fil_slc = [slice(None), slice(None), slice(None)]
            if isinstance(slc, tuple) or isinstance(slc, list):
                for i in range(len(slc)):
                    if isinstance(slc[i], int) or isinstance(slc[i], np.int32) or isinstance(slc[i], np.int64):
                        fil_slc[2-i] = slice(slc[i], slc[i]+1)
                    else:
                        fil_slc[2-i] = slc[i]
            fil_slc = tuple(fil_slc)

            # No indications present in restarts to read any fancy indexing. Only support the basics
            i = self.index_of(var)
            if i is not None:
                # This is one of the main vars in the 'prims' array
                arr = fil['/p'][(i,) + fil_slc][()]
                if len(arr.shape) > 3:
                    self.cache[var] = np.squeeze(np.einsum("pkji->pijk", arr))
                else:
                    self.cache[var] = np.squeeze(np.einsum("kji->ijk", arr))
                return self.cache[var]
            else:
                raise IOError("Cannot find variable "+var+" in file "+self.fname+"!")
