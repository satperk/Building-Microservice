from flask import Flask, render_template, request, jsonify
import os
import requests
from datetime import datetime, timedelta, time, timezone, tzinfo
import re

app = Flask(__name__)
weekdays = ('M','T', 'W', 'R', 'F', 'Sat', 'Sun')
currenttime = datetime.now(timezone.utc)

# Route for "/" (frontend):
@app.route('/')
def index():
  return render_template("index.html")


# Route for "/weather" (middleware):
@app.route('/weather', methods=["POST"])
def POST_weather():
  course = request.form["course"]
  match = re.match(r"([A-Za-z]+)[\s]*?([0-9]+)", course, re.I)
  items = []
  if match:
      items = match.groups()
  subject = items[0].upper()
  number = items[1]

  # Ensure `subject` contains the subject (ex: "CS") and `number` contains the course number (ex: 240).
  server_url = os.getenv('COURSES_MICROSERVICE_URL')
  r = requests.get(f'{server_url}/{subject}/{number}/')
  course_data = r.json()
  print(course_data)
  if (int(r.status_code) != 200):
    return jsonify("Course info not available"), 404
  
  #
  # get weather data
  #
  forecast_data = get_weather_data(40.1125,-88.2284)

  # weekday_to_ind = {'M':0, 'T':1, 'W':2, 'R':3, 'F':4, 'Sat':5, 'Sun':6}

  class_days = []
  for i in course_data['Days of Week']:
    class_days.append(i)
  class_time = course_data['Start Time']
  if len(class_days) == 0 :
    return jsonify("Course info not available"), 404

    
  print('\n',course_data, '\n')
  print(class_days, class_time)
  classtime_split = re.split(':|\s',class_time)

  classmeeting, nearestDay = getNextMeeting(class_days, classtime_split)
  classhr = classmeeting.hour
  classmin = classmeeting.minute
  classday_forecast = []
  print("NEAREST", nearestDay)
  #filter the forecast data and get the info for the nearest class meeting day
  for i,p in enumerate(forecast_data['properties']['periods']):
    x = datetime.fromisoformat(p['startTime'])
    if (weekdays[x.weekday()] == nearestDay) :
      classday_forecast.append(p)
  
  #look through filtered data to find the time that is closest to class time
  mindiff = timedelta.max
  forecast = ''
  for f in (classday_forecast):
    x = datetime.fromisoformat(f['startTime']) - timedelta(hours=5)
    diff = x - classmeeting
    print(diff)
    
    # to make sure we are finding times that are not negative more than 30 minutes
    if (diff <= timedelta(hours=-1)):
      continue

    if diff < mindiff:
      mindiff = diff
      forecast = f

  print(forecast)

  #format classmeeting time
  year = classmeeting.strftime("%Y")
  month = classmeeting.strftime("%m")
  day = classmeeting.strftime("%d")
  time = classmeeting.strftime("%H:%M:%S")

  ftime = datetime.fromisoformat(forecast['startTime'])

  fyear = ftime.strftime("%Y")
  fmonth = ftime.strftime("%m")
  fday = ftime.strftime("%d")
  ft = ftime.strftime("%H:%M:%S")

  ncm = f"{year}-{month}-{day} {time}"
  fct = f"{fyear}-{fmonth}-{fday} {ft}"

  print(ncm, fct)
  toreturn = {
    "course": course_data['course'],
    "nextCourseMeeting": ncm,
    "forecastTime": fct,
    "temperature": forecast['temperature'],
    "shortForecast": forecast['shortForecast']
  
  }
  return jsonify(toreturn), 200


def get_weather_data(lat, long):
  #use the coordinates to retrieve the grid data and office that we need to use
  latitude =  lat
  longitude = long
  point_url = 'https://api.weather.gov/points'
  r = requests.get(f'{point_url}/{latitude},{longitude}/')
  points_data = r.json()
  office = points_data['properties']['gridId']  #ILX
  grid_x = points_data['properties']['gridX']   #95
  grid_y = points_data['properties']['gridY']   #71

  print(office, grid_x, grid_y)

  #get forecast data
  forecast_url = 'https://api.weather.gov/gridpoints/'
  r = requests.get(f'{forecast_url}/{office}/{grid_x},{grid_y}/forecast/hourly')
  forecast_data = r.json()
  return forecast_data

def getNextMeeting(days, t):
  # make a date time object from the days
  print(currenttime, weekdays[currenttime.weekday()])
  #find closest day

  min = 7
  day = ''
  for d in days:
    diff = (weekdays.index(d) - currenttime.weekday())
    if diff < 0:
      diff += 7
    if diff < min:  
      #find min difference--> closest day
      min = diff
      day = d
  print(days, t, day, min)

  # create a datetime obj using current time + offset (min)
  classdt = datetime(currenttime.year,currenttime.month, currenttime.day, tzinfo=timezone.utc)
  classdt = classdt + timedelta(days=min)
  #add time info
  classhr = int(t[0])
  classmin = int(t[1])
  if t[2] == 'PM' and classhr != 12:
    classhr += 12
  classdt = classdt + timedelta(hours=classhr, minutes=classmin)
  print('class: ' , classdt)

  return classdt, day
