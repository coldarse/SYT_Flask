from cgi import test
from itertools import count
from textwrap import indent
from flask import Flask, render_template, json, url_for, request, redirect
# import RPi.GPIO as GPIO
from datetime import datetime
import os

app = Flask(__name__)

SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
json_url  = os.path.join(SITE_ROOT, "static", "data.json")

# GPIO.setmode(GPIO.BCM)
# GPIO.setwarnings(False)

@app.route("/")
def dashboard():
    availableGPIO = json.load(open(json_url))
    
    # for gPIO in availableGPIO['GPIOs']:
    #     GPIO.setup(
    #             gPIO['No'], 
    #             GPIO.IN if gPIO['Type'] == input else GPIO.OUT
    #         )
    #     status = GPIO.input(gPIO['No'])
    #     updateArray(gPIO['No'], status)
    
    return render_template(
            "dashboard.html",
            len = len(availableGPIO['GPIOs']),
            gpios = availableGPIO['GPIOs']
        )


@app.route("/GPIO/")
@app.route("/GPIO/<no>")
def gpio(no = None):
    availableGPIO = json.load(open(json_url))
    
    selected = None
    for gPIO in availableGPIO['GPIOs']:
        if str(gPIO['No']) == str(no):
            selected = gPIO
            break
        
        
    return render_template(
            "gpio.html", 
            len = len(availableGPIO['GPIOs']), 
            gpios = availableGPIO['GPIOs'], 
            no = selected
        )
    
@app.route("/GPIO/", methods=['POST'])
def gpio_post():
    no = request.form['gpioNo']
    return redirect(url_for("gpio", no = str(no)))
    
@app.route("/GPIO/<no>", methods=['POST'])
def gpio_no_post(no = None):
    
    if request.form['update'] == 'Submit':
        gpioName      = request.form['gpioName']
        availableGPIO = json.load(open(json_url))
        
        for gPIO in availableGPIO['GPIOs']:
            if str(gPIO['No']) == str(no):
                gPIO['Name'] = gpioName
                break
        
        with open(json_url, 'w') as file:
            json.dump(availableGPIO, file, indent=4)
        
    return redirect(url_for("gpio", no = None))


# ----- For Updating Status and Activites of Specific GPIO -----#
def updateArray(no = None, status = None):
    availableGPIO = json.load(open(json_url))
    for gPIO in availableGPIO['GPIOs']:
        if str(gPIO['No']) == str(no):
            
            if status == 1:
                gPIO['Status'] = 'Online'
            elif status == 0:
                gPIO['Status'] = 'Offline'
            else:
                gPIO['Status'] = 'Undefined'
            
            tempActivityArray = []
                
            for activity in gPIO['Activities']:
                tempActivityArray.append(activity)
                
            tempActivityArray.append({
                    "Time": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                    "Activity": gPIO['Status']
                })
            
            if len(tempActivityArray) > 5:
                tempActivityArray.pop(0)
                
            gPIO['Activities'] = tempActivityArray
                
            with open(json_url, 'w') as file:
                json.dump(availableGPIO, file, indent=4)
            
    