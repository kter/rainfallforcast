# -*- coding: utf-8 -*-
#!/usr/bin/python

# TODO: DynamoDBに現在雨が降っているかの状態を登録し、メッセージの出し分けをする

import requests
from datetime import datetime, timedelta
import json
from pygooglechart import Chart
from pygooglechart import SimpleLineChart
from pygooglechart import Axis
import math
from pyshorteners import Shortener
import ConfigParser
from slackclient import SlackClient
import time

inifile = ConfigParser.SafeConfigParser()
inifile.read("./config.ini")
GOOGLE_API_KEY = inifile.get('rainfall', 'google_api_key')
YAHOO_APP_ID = inifile.get('rainfall', 'yahoo_app_id')
LON = inifile.get('rainfall', 'lon')
LAT = inifile.get('rainfall', 'lat')
MAP_IMAGE_X = inifile.get('rainfall', 'map_image_x')
MAP_IMAGE_Y = inifile.get('rainfall', 'map_image_y')
ALERT_THRESH = inifile.get('rainfall', 'alert_thresh')
ZOOM = inifile.get('rainfall', 'zoom')

def getTimeString(offset_minutes):
    d = datetime.now() + timedelta(hours=9, minutes=offset_minutes)
    return d.strftime("%H:%M")

def getRainfallRadarUrl(lat, lon, zoom, width, height):
    # http://developer.yahoo.co.jp/webapi/map/openlocalplatform/v1/static.html#exp_weather
    url = "http://map.olp.yahooapis.jp/OpenLocalPlatform/V1/static?appid=" + YAHOO_APP_ID + "&lat=" + str(lat) + "&lon=" + str(lon) + "&z=" + str(zoom) + "&width=" + str(width) + "&height=" + str(height) + "&overlay=type:rainfall"
    return url

def shorten_url(url):
    shortener = Shortener('Google', api_key=GOOGLE_API_KEY)
    return shortener.short(url)

def lambda_handler(event, context):
    # http://developer.yahoo.co.jp/webapi/map/openlocalplatform/v1/weather.html
    
    url = "http://weather.olp.yahooapis.jp/v1/place"
    
    payload = {'appid': YAHOO_APP_ID, 'coordinates': LON + "," + LAT, 'output': 'json'}
    result =  requests.get(url, params=payload)
    
    timeString = getTimeString(30)
    send_message = False
    
    json_data = json.loads(result.content)
    
    rainfall = json_data['Feature'][0]['Property']['WeatherList']['Weather']#[3]['Rainfall']
    
    if rainfall[3]['Rainfall'] >= ALERT_THRESH:
        send_message = True
        message = timeString + "で" + str(rainfall[3]['Rainfall']) + "mm/hの雨が予想されます。"
    elif rainfall[3]['Rainfall'] < ALERT_THRESH:
        send_message = True
        message = timeString + "で" + str(rainfall[3]['Rainfall']) + "mm/hの雨が予想されます。"
    else:
        send_message = True
        message = timeString + ": 多分降水量が取れてないです。"
    
    if send_message == True:
    
        width = 500
        height = 150
        chart = SimpleLineChart(width, height)
        chart.set_colours(['719CFF'])
    
        rainfall_array = [rainfall[0]['Rainfall'], rainfall[1]['Rainfall'], rainfall[2]['Rainfall'], rainfall[3]['Rainfall'], rainfall[4]['Rainfall'], rainfall[5]['Rainfall'], rainfall[6]['Rainfall']]
        chart.add_data(rainfall_array)
        
        chart.set_axis_labels(Axis.BOTTOM, [getTimeString(0), getTimeString(10), getTimeString(20), getTimeString(30), getTimeString(40), getTimeString(50), getTimeString(60)])
        chart.set_legend(['Rainfall(mm/h)'])
        chart.set_legend_position('bv')
    
        if math.ceil(max(rainfall_array)) < 1.0:
            chart.y_range=(0, 1)
            chart.set_axis_range(Axis.LEFT, 0, 1)
        else:
            chart.y_range=(0, math.ceil(max(rainfall_array)))
            chart.set_axis_range(Axis.LEFT, 0, math.ceil(max(rainfall_array)))
    
        d = datetime.now() + timedelta(hours=9, minutes=30)
        date_str = d.strftime("|date:%Y%m%d%H%M|datelabel:on")
    
        radar_url = "http://weather.yahoo.co.jp/weather/zoomradar/?lat=" + LAT + "&lon=" + LON + "&z=12"
        rainfall_image_url = getRainfallRadarUrl(LAT, LON, ZOOM, MAP_IMAGE_X, MAP_IMAGE_Y) + date_str
    
        chart_url = shorten_url(chart.get_url())
        rainfall_image_url = shorten_url(rainfall_image_url)
        radar_url = shorten_url(radar_url)
    
        message = unicode(message, 'utf-8') + "\n" + chart_url + "\n" + timeString + u"の雨雲予想図: " + rainfall_image_url + "\n" + u"詳細: " + radar_url + "\n"
    
        sc = SlackClient(inifile.get('slack', 'token'))
        res = sc.api_call("chat.postMessage", channel=inifile.get('slack', 'channel'), text=message, username=inifile.get('slack', 'username'), icon_emoji=inifile.get('slack', 'icon_emoji'))
        print(res)
