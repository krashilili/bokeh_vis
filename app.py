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
import matplotlib.pyplot as plt
import io
import base64
import requests
from datetime import date, datetime


app = Flask(__name__)


@app.route("/td")
def test_data():
    data = get_data()
    dj = data.json()

    color_list = ['green', 'red', 'blue', 'black']
    legend_list = ['Passed', 'Failed', 'Blocked', 'Total']

    # slice off the first element
    xax = (dj['data']['columns'][0])[1:]
    fail = (dj['data']['columns'][1])[1:]
    not_run = (dj['data']['columns'][2])[1:]
    in_progress = (dj['data']['columns'][3])[1:]
    blocked = (dj['data']['columns'][4])[1:]
    passed = (dj['data']['columns'][5])[1:]
    total = (dj['data']['columns'][6])[1:]

    dates_list = [datetime.strptime(x, '%Y-%m-%d').date() for x in xax]

    ys = [passed, fail, blocked, total]
    xs = [dates_list, dates_list, dates_list, dates_list]

    p = figure(plot_height=400, title="Test Cases", plot_width=750, x_axis_type='datetime')

    for (colr, leg, x, y) in zip(color_list, legend_list, xs, ys):
        p.line(x, y, color=colr, legend=leg)

    # multiline example too, but it does not do a legend per line
    # p.multi_line(xs=[dates_list, dates_list,dates_list, dates_list], ys=[passed, not_run, blocked, fail])

    p.xaxis.major_label_orientation = 3 / 4
    p.legend.location = "top_left"

    # create data for rendering...
    p1 = p
    p_dict = {'not_run': p1}

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


def get_data():
    r = requests.get('http://qmetry-data.ece.delllabs.net:8080/api/timeseries?type=timeseries&release=settlers&about=status')
    return r


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
