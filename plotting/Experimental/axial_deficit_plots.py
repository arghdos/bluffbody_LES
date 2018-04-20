import matplotlib.pyplot as plt

from read_simulation_data import read_simulation_data
from read_experimental_data import read_experimental_data
from common import get_default_parsing_args

graph_name = 'axialDeficitPlot_{point}'


def plot(case, reacting, t_start=0, t_end=-1):
    for point in ['0point95', '1point53', '3point75', 'point375', '9point4']:
        name = graph_name.format(point=point)
        expdata = read_experimental_data(name, args.reacting)
        simdata = read_simulation_data(case, name, reacting, t_start, t_end)
        # normalize / convert simulation data
        simdata.normalize(reacting)

        plt.plot(expdata[:, 0], expdata[:, 1], label=expdata.name)
        plt.plot(simdata[:, 0], simdata[:, 1], label=simdata.name)
        plt.xlabel(expdata.columns[1])
        plt.ylabel(expdata.columns[0])
        plt.legend(loc=0)
        plt.savefig('axial_deficit_plot_{point}.pdf'.format(point=point))


if __name__ == '__main__':
    parser = get_default_parsing_args(
        'mean_axial_velocity.py',
        'plots the time-averaged, normalized axial velocity '
        'along the centerline of the Volvo bluff-body experiment, as compared '
        'to experimental data')
    args = parser.parse_args()

    plot(args.case, args.reacting, args.start_time, args.end_time)
