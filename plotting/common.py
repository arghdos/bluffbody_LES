"""
common.py -- a set of common data objects / plotting styles for plotting of
Volvo LES bluff-body

Nick Curtis

04/19/2018
"""
from __future__ import division

from argparse import ArgumentParser
import os
from os.path import join as pjoin
from os.path import pardir as ppardir
from os.path import isdir as pisdir
import numpy as np
import matplotlib.pyplot as plt

script_dir = os.path.abspath(os.path.dirname(__file__))


class dimensions(object):
    def __init__(self, reacting=False):
        self.D = 40 / 1000  # mm
        self.height = 3 * self.D
        self.width = 2 * self.D
        self.Ubulk = 16.6 if not reacting else 17.6  # m/s
        self.trailing_edge = -200 / 1000  # mm
        self.z_offset = self.trailing_edge  # mm
        self.y_offset = self.height / 2  # mm
        self.z_flip = -1


class dataset(object):
    def __init__(self, columns, data, name, is_simulation=False):
        """
        Attributes
        ----------
        columns: list of str
            The column header names, read from the experimental data
        data: numpy array of shape (len(columns), :attr:`npoints`)
            The data in the experimental data set
        name: str
            The experimental data filename, describing the data within
        is_simulation: bool [False]
            Whether the data is from a simulation or not
        """

        self.columns = columns[:]
        self.data = np.copy(data)
        self.name = name
        self.is_simulation = is_simulation

        assert len(columns) == data.shape[1]

    @property
    def npoints(self):
        """
        The number of data points in this data set
        """
        return self.data.shape[1]

    @property
    def shape(self):
        return self.data.shape

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value

    def normalize(self, reacting=False):
        assert self.is_simulation, "I don't know how to normalize experimental data"

        dims = dimensions(reacting)
        for i, col in enumerate(self.columns):
            if col in ['y', 'z']:
                # correct dimensions
                offset = getattr(dims, '{}_offset'.format(col), 0)
                self.data[:, i] -= offset
                # flip axes?
                flip = getattr(dims, '{}_flip'.format(col), 1)
                self.data[:, i] *= flip
                # normalize
                self.data[:, i] /= dims.D
            elif col in ['Ux', 'Uy', 'Uz']:
                axis = col[-1]
                if 'fluct' not in self.name:
                    # flip axes?
                    flip = getattr(dims, '{}_flip'.format(axis), 1)
                    self.data[:, i] *= flip
                Ubulk = dims.Ubulk
                # and normalize
                self.data[:, i] /= Ubulk


class PlotStyles(object):
    def __init__(self, cases, grey=False):
        self.num_colors = len(cases) + 1  # for experimental data
        self.grey = grey

    @property
    def color_map(self):
        cmap = 'Greys' if self.grey else 'inferno'
        return plt.get_cmap(cmap, self.num_colors + 1)


class UserOptions(object):
    """
    A simple class that holds the various user-specified options
    """

    def __init__(self, cases, reacting, t_start=0, t_end=-1,
                 base_path=None, out_path=None, velocity_component='both'):
        self.cases = cases
        self.reacting = reacting
        self.t_start = t_start
        self.t_end = t_end
        self.base_path = base_path
        self.out_path = out_path
        self.velocity_component = velocity_component
        if self.velocity_component == 'both':
            self.velocity_component = ['z', 'y']
        else:
            self.velocity_component = [self.velocity_component]
        # fix case paths
        self.cases = self.get_cases()
        if self.out_path is None:
            self.out_path = script_dir

        # plot styles
        self.style = PlotStyles(self.cases)

    @property
    def ncases(self):
        return len(self.cases)

    def get_simulation_path(self, case, graph_name):
        """
        Return the path to a simulation graph directory
        """
        path = pjoin(self.base_path, case, 'postProcessing', graph_name)
        path = os.path.abspath(path)

        if not pisdir(path):
            raise Exception('Graph {} for case {} {} not found, {} is not a valid '
                            'directory'.format(
                                graph_name,
                                'reacting' if self.reacting else 'non-reacting',
                                case, path))

        return path

    def make_dir(self, case):
        import os
        if not os.path.exists(pjoin(self.out_path, case)):
            os.makedirs(pjoin(self.out_path, case))

    def get_cases(self):
        # get path
        if self.base_path:
            self.base_path = os.path.abspath(self.base_path)
        else:
            self.base_path = os.path.abspath(pjoin(script_dir, ppardir))
        react_str = 'reacting' if self.reacting else 'non-reacting'
        self.base_path = pjoin(self.base_path, react_str)
        return [pjoin(self.base_path, case) for case in self.cases]

    def color(self, caseno, exp=False):
        return self.style.color_map(caseno + 1 if not exp else 0)


def get_default_parsing_args(name, description):
    parser = ArgumentParser('{name}: {description}'.format(
        name=name, description=description))
    parser.add_argument('-r', '--reacting',
                        help='Plot the reacting-flow data.',
                        action='store_true',
                        dest='reacting',
                        default=False,
                        required=False)
    parser.add_argument('-n', '--non_reacting',
                        help='Plot the reacting-flow data.',
                        action='store_false',
                        dest='reacting',
                        required=False)
    parser.add_argument('-c', '--caselist',
                        type=str,
                        help='The simulation(s) to plot. If more than one simulation'
                             ' is supplied, they will be plotted on the same figure'
                             " in the first supplied case's directory.",
                        nargs='+',
                        required=True)
    parser.add_argument('-t_start', '--start_time',
                        help='The start time for simulation averaging in seconds.',
                        required=False,
                        type=float,
                        default=0)
    parser.add_argument('-t_end', '--end_time',
                        help='The end time for simulation averaging in seconds.',
                        required=False,
                        type=float,
                        default=-1)
    parser.add_argument('-p', '--base_path',
                        default=None,
                        type=str,
                        help='The base path to the top-level folder that contains '
                             'the non-reacting and reacting cases.')
    parser.add_argument('-o', '--out_path',
                        required=False,
                        default=None,
                        help='The path to place the generated plots in. '
                             'If not supplied, stores in the case-directory')
    return parser
