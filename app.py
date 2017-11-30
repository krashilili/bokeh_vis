import random
from bokeh.models import (HoverTool, FactorRange, Plot, LinearAxis, Grid,
                          Range1d, SingleIntervalTicker, DatetimeTickFormatter)
from bokeh.models.glyphs import VBar
from bokeh.io import show, output_file
from bokeh.plotting import figure
from bokeh.embed import components
from bokeh.resources import INLINE
from bokeh.util.string import encode_utf8
from flask import Flask, render_template, jsonify
from bokeh.models import ColumnDataSource
from bokeh.models.widgets import DataTable, DateFormatter, TableColumn
from random import randint
from bokeh.layouts import widgetbox

import matplotlib.pyplot as plt
import io
import base64
import requests
from datetime import date, datetime


app = Flask(__name__)

BASIC_URL = 'http://qmetry-data.ece.delllabs.net:8080/api/'


def get_data(**kwargs):
    if 'build' in kwargs:
        url = BASIC_URL+'{type}?type={type}&release={release}&build={build}&about={about}'
    else:
        url = BASIC_URL + '{type}?type={type}&release={release}&about={about}'
    my_url = url.format(**kwargs)
    resp = requests.get(my_url)
    d=resp.json()
    return resp.json()


def lines(xs, ys, legend_list, color_lsty_list, fig_title):
    hover = HoverTool(
        tooltips=[
            ('date', '$x{%F}'),  # convert date to float
            ('count', '$y{0}')
        ],

        formatters={
            '$x': 'datetime',  # use 'datetime' formatter for '$x' field
        },

        # display a tooltip whenever the cursor is vertically in line with a glyph
        mode='vline'
    )

    p = figure(plot_height=500, title=fig_title, plot_width=800, x_axis_type='datetime')
    p.add_tools(hover)

    for (colr_lsty, leg, x, y) in zip(color_lsty_list, legend_list, xs, ys):
        p.line(x, y, color=colr_lsty[0], legend=leg, line_dash=colr_lsty[1], line_width=2)

    # multiline example too, but it does not do a legend per line
    # p.multi_line(xs=[dates_list, dates_list,dates_list, dates_list], ys=[passed, not_run, blocked, fail])

    p.xaxis.major_label_orientation = 3 / 4
    p.legend.location = "top_left"
    p.legend.click_policy = "hide"

    # create data for rendering...
    p1 = p
    p_dict = {'test_case_data': p1}

    script, div = components(p_dict)

    # grab the static resources
    js_resources = INLINE.render_js()
    css_resources = INLINE.render_css()

    html = render_template(
        'chart.html',
        plot_script=script,
        plot_div=div,
        plot_type='lines',
        js_resources=js_resources,
        css_resources=css_resources,
    )
    return encode_utf8(html)


def data_table(data, column_names):
    # data = dict(
    #     dates=[date(2014, 3, i + 1) for i in range(10)],
    #     downloads=[randint(0, 100) for i in range(10)],
    # )

    source = ColumnDataSource(data)

    columns = [
        TableColumn(field=n, title=n.upper()) for n in column_names
        # TableColumn(field="dates", title="Date", formatter=DateFormatter()),
        # TableColumn(field="downloads", title="Downloads"),
    ]
    w1 = DataTable(source=source, columns=columns, width=600, height=280)
    script, div = components(w1)

    # grab the static resources
    js_resources = INLINE.render_js()
    css_resources = INLINE.render_css()

    html = render_template(
        'chart.html',
        plot_script=script,
        plot_div=div,
        plot_type='datatable',
        js_resources=js_resources,
        css_resources=css_resources,
    )
    return encode_utf8(html)


@app.route("/lines/<release>/<build>")
def test_data(release, build):
    kwargs = {
        'type': 'timeseries',
        'release': '%s'%(release),
        'build': '%s'%(build), # 100% attempt
        'about': 'status'
    }
    dj = get_data(**kwargs)['data']['columns']

    status_cnt = len(dj) - 1
    status_color_lsty = {
        'passed': ('seagreen', 'solid'),
        'failed': ('firebrick','solid'),
        'blocked':('orange',   'solid'),
        'not run':('lightblue','solid'),
        'in progress':('orchid','solid'),
        'total':  ('black',   'dotdash')
    }

    # slice off the first element
    dates_list = [datetime.strptime(x, '%Y-%m-%d').date() for x in dj[0][1:]]

    xs = [dates_list for m in range(1, status_cnt + 1)]
    ys = [dj[i][1:] for i in range(1,status_cnt+1)]
    legend_list = [dj[j][0] for j in range(1, status_cnt+1)]

    color_lsty_list = [[status_color_lsty[status.lower()][0], status_color_lsty[status.lower()][1]] \
                              for status in [dj[i][0] for i in range(1, status_cnt+1)]]

    lines_html = lines(xs, ys, legend_list, color_lsty_list, fig_title='Test Cases')

    return lines_html


@app.route("/datatable/<release>")
def dt_release(release):
    kwargs = {
        'type':'dtable',
        'about':'group',
        'release':release,
    }
    raw_data = get_data(**kwargs)
    groups = [ e['Group'] for e in raw_data]
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
    return data_table(data,column_names=data.keys())


@app.route("/<int:bars_count>")
def chart(bars_count):
    if bars_count <= 0:
        bars_count = 1
    return render_template("chart.html", bars_count=bars_count)


@app.route('/bokeh')
def bokeh():
    # init a basic bar chart:
    # http://bokeh.pydata.org/en/latest/docs/user_guide/plotting.html#bars
    fig = figure(plot_width=600, plot_height=600)
    fig2 = figure(plot_width=600, plot_height=600)
    fig.vbar(
        x=[1, 2, 3, 4],
        width=0.5,
        bottom=0,
        top=[1.7, 2.2, 4.6, 3.9],
        color='navy'
    )

    fig2.vbar(
        x=[1 / 1, 2 / 8, 3, 4, 8],
        width=0.5,
        bottom=0,
        top=[1.7, 2.2, 4.6, 3.9, 12.55],
        color='navy'
    )

    plots = {'red': fig, 'blue': fig2}

    # grab the static resources
    js_resources = INLINE.render_js()
    css_resources = INLINE.render_css()

    # render template
    script, div = components(plots)

    html = render_template(
        'chart.html',
        plot_script=script,
        plot_div=div,
        js_resources=js_resources,
        css_resources=css_resources,
    )
    return encode_utf8(html)


@app.route('/plot')
def build_plot():
    img = io.BytesIO()

    y = [1, 2, 3, 4, 5]
    x = [0, 2, 1, 3, 4]
    plt.plot(x, y)
    plt.savefig(img, format='png')
    img.seek(0)

    plot_url = base64.b64encode(img.getvalue()).decode()

    return '<img src="data:image/png;base64,{}">'.format(plot_url)


@app.route('/p')
def p():

    p1 = build_p()
    p_dict = {'yellow': p1}

    script, div = components(p_dict)

    # grab the static resources
    js_resources = INLINE.render_js()
    css_resources = INLINE.render_css()

    html = render_template(
        'chart.html',
        plot_script=script,
        plot_div=div,
        js_resources=js_resources,
        css_resources=css_resources,
    )
    return encode_utf8(html)


def build_p():
    output_file("bars.html")

    fruits = ['Apples', 'Pears', 'Nectarines', 'Plums', 'Grapes', 'Strawberries']

    p = figure(x_range=fruits, plot_height=350, title="Fruit Counts",
               toolbar_location=None, tools="")

    p.vbar(x=fruits, top=[5, 3, 4, 2, 4, 6], width=0.3)

    p.xgrid.grid_line_color = None
    p.y_range.start = 0

    return p


if __name__ == '__main__':
    app.run(debug=True)
