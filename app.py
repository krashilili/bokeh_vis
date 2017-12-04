import random
from collections import namedtuple
from bokeh.models import (HoverTool, FactorRange, Plot, LinearAxis, Grid,
                          Range1d, SingleIntervalTicker, DatetimeTickFormatter)
from bokeh.models.glyphs import VBar
from bokeh.io import show, output_file
from bokeh.plotting import figure
from bokeh.embed import components
from bokeh.resources import INLINE
from bokeh.util.string import encode_utf8
from flask import Flask, render_template
from bokeh.palettes import Viridis3
from bokeh.layouts import gridplot

import matplotlib.pyplot as plt
import io
import base64

from datetime import date, datetime
from math import pi

from chart_template import *

app = Flask(__name__)


def get_timeseries_data(release, build=None,start_on=None, end_on=None, fig_title=None):
    kwargs = {
        'type': 'timeseries',
        'release': release,
        'about': 'status'
    }
    build_name = "All Cycles"

    if build:
        kwargs.update({'build': build})
        build_name = build

    if start_on:
        kwargs.update({'start_date': start_on})
        start_date = start_on
    if end_on:
        kwargs.update({'end_date': end_on})
        end_date = end_on

    dj = get_data(**kwargs)['data']['columns']

    status_cnt = len(dj) - 1
    status_color_lsty = {
        'passed': ('seagreen', 'solid'),
        'failed': ('firebrick', 'solid'),
        'blocked': ('orange', 'solid'),
        'not run': ('lightblue', 'solid'),
        'in progress': ('orchid', 'solid'),
        'total': ('black', 'dotdash')
    }

    # slice off the first element
    dates_list = [datetime.strptime(x, '%Y-%m-%d').date() for x in dj[0][1:]]
    cnt = status_cnt + 1
    xs = [dates_list for _ in range(1, cnt)]
    ys = [dj[i][1:] for i in range(1, cnt)]
    legend_list = [dj[j][0] for j in range(1, cnt)]

    color_lsty_list = [[status_color_lsty[status.lower()][0], status_color_lsty[status.lower()][1]] \
                       for status in [dj[i][0] for i in range(1, status_cnt + 1)]]

    return xs, ys, legend_list, color_lsty_list, fig_title


def get_datatable_data(release):
    kwargs = {
        'type': 'dtable',
        'about': 'group',
        'release': release,
    }
    raw_data = get_data(**kwargs)
    groups = [e['Group'] for e in raw_data]
    not_run = [e['Not Run'] for e in raw_data]
    blocked = [e['Blocked'] for e in raw_data]
    passed = [e['Passed'] for e in raw_data]
    failed = [e['Failed'] for e in raw_data]
    in_prg = [e['In Progress'] for e in raw_data]
    tlt = [e['Total'] for e in raw_data]
    data = dict(
        groups=groups,
        not_run=not_run,
        blocked=blocked,
        passed=passed,
        failed=failed,
        in_progress=in_prg,
        tlt=tlt
    )
    return data


@app.route('/bar/platform/<release>')
def bar_by_platform(release):
    kwargs = {
        'type': 'bar',
        'about': 'platform',
        'release': release,
    }

    raw_data = get_data(**kwargs)['data']['columns']
    bc = raw_data[0][1:]
    bvs = raw_data[1:]
    return get_nested_bar_html(fig_title='Bar by Platform',bar_category=bc, bar_values=bvs)


@app.route('/bar/tester/<release>')
def bar_by_tester(release):
    kwargs = {
        'type': 'bar',
        'release': release,
        'about': 'tester'
    }
    raw_data = get_data(**kwargs)['data']['columns']
    bc = raw_data[0][1:]
    bvs = raw_data[1][1:]
    return get_bar_html(bar_category=bc, bar_values=bvs,fig_title='Tester')


@app.route('/timeseries/status/<release>')
@app.route('/timeseries/status/<release>/')
@app.route('/timeseries/status/<release>/<build>')
@app.route('/timeseries/status/<release>/<build>/<start_on>/<end_on>')
def time(release, build=None,start_on=None, end_on=None):
    return get_timeseries_html(release, build, start_on, end_on)


@app.route("/datatable/<release>")
def datatable_release(release):
    html = get_datatable_html(release)
    return html


@app.route('/pie/ts/<release>')
def pie_tc_status(release):
    """
    :param release:
    :return:
    """
    kwargs = {
        'type': 'pie',
        'about': 'status',
        'release': release,
    }
    raw_data = get_data(**kwargs)

    vals = [int(v[1]) for v in raw_data.items()]
    tlt = sum(vals)
    # created data_groups = [(category, percentage, color, count),...]
    data = [(v[0], v[1] / tlt, STATUS_COLORS.get(v[0].lower()), v[1]) for v in raw_data.items()]

    pie_html = get_pie_html(data, 'Pie Chart')
    return pie_html


@app.route('/pie/tg/<release>')
def pie_tg(release):
    kwargs = {
        'type':'pie',
        'about':'group',
        'release':release
    }
    raw_data = get_data(**kwargs)
    tlt = sum([int(v[1]) for v in raw_data.items()])
    colors = {'vendor':'blue',
              'dell':'orange'}
    # created data_groups = [(category, percentage, color, count),...]
    data_groups = [ (v[0], v[1]/tlt, colors.get(v[0].lower()), v[1]) for v in raw_data.items()]
    pie_html = get_pie_html(fig_title='Test Group', data=data_groups)

    return pie_html


@app.route('/mixed/<release>')
def m(release):
    # create widgets

    # timeseries
    s1_data = get_timeseries_data(release=release,build='pass-2',fig_title='Timeseries by Pass-2')
    s1 = get_timeseries_widget(*s1_data)

    s2_data = get_datatable_data(release)
    s2 = get_datatable_widget(s2_data)

    # create pie data of testcase status
    kwargs = {
        'type': 'pie',
        'about': 'status',
        'release': release,
    }
    raw_data = get_data(**kwargs)

    vals = [int(v[1]) for v in raw_data.items()]
    tlt = sum(vals)
    # create data_groups = [(category, percentage, color, count),...]
    s3_data = [(v[0], v[1] / tlt, STATUS_COLORS.get(v[0].lower()), v[1]) for v in raw_data.items()]
    s3 = get_pie_widget(s3_data, fig_title='Pie by TC Status')

    # create pie data of test group
    kwargs = {
        'type': 'pie',
        'about': 'group',
        'release': release
    }
    raw_data = get_data(**kwargs)
    tlt = sum([int(v[1]) for v in raw_data.items()])
    colors = {'vendor': 'blue',
              'dell': 'orange'}
    # create data_groups = [(category, percentage, color, count),...]
    s4_data = [(v[0], v[1] / tlt, colors.get(v[0].lower()), v[1]) for v in raw_data.items()]
    s4 = get_pie_widget(s4_data, fig_title='Pie by Test Group')

    # nested bar: test cases by platform
    kwargs = {
        'type': 'bar',
        'about': 'platform',
        'release': release,
    }

    raw_data = get_data(**kwargs)['data']['columns']
    nested_bc = raw_data[0][1:]
    nested_bvs = raw_data[1:]
    s5 = get_nested_bar_widget(bar_category=nested_bc, bar_values=nested_bvs,fig_title='Nested Bar by Platform')

    # bar: testcases by tester
    kwargs = {
        'type': 'bar',
        'release': release,
        'about': 'tester'
    }
    raw_data = get_data(**kwargs)['data']['columns']
    bc = raw_data[0][1:]
    bvs = raw_data[1][1:]
    s6 = get_bar_widget(bar_category=bc, bar_values=bvs, fig_title='Bar by Tester')

    # make a grid
    grid = gridplot([s1, s2, s3, s4,s5,s6], ncols=2, plot_width=500, plot_height=500)
    script, div = components(grid)
    # grab the static resources
    js_resources = INLINE.render_js()
    css_resources = INLINE.render_css()
    html = render_template(
        'chart.html',
        plot_script=script,
        plot_div=div,
        plot_type='multi',
        js_resources=js_resources,
        css_resources=css_resources,
    )
    return encode_utf8(html)


if __name__ == '__main__':
    app.run(debug=True)
