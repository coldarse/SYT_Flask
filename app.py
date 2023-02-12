from flask import Flask, render_template, json, send_file, url_for, request, redirect, Response
import RPi.GPIO as GPIO
from datetime import datetime
import os
import time
# import threading
import csv

import base64
import hashlib
from Crypto.Cipher import AES
from Crypto import Random

app = Flask(__name__)

SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
json_url  = os.path.join(SITE_ROOT, "static", "data.json")

logs_url = os.path.join(SITE_ROOT, "static", "logs")
gPIO_header = ['Time', 'Activity']

BLOCK_SIZE = 16
pad = lambda s: s + (BLOCK_SIZE - len(s) % BLOCK_SIZE) * chr(BLOCK_SIZE - len(s) % BLOCK_SIZE)
unpad = lambda s: s[:-ord(s[len(s) - 1:])]

def encrypt(plain_text, key):
    private_key = hashlib.sha256(key.encode("utf-8")).digest()
    plain_text = pad(plain_text)
    cipher = AES.new(private_key, AES.MODE_ECB)
    return base64.b64encode(cipher.encrypt(plain_text.encode("utf-8")))


# ----- For Updating Status and Activites of Specific GPIO -----#
def updateArray(no = None, status = None):
    availableGPIO = json.load(open(json_url))
    
    for gPIO in availableGPIO['GPIOs']:
        if str(gPIO['No']) == str(no):
            statusStr = ''
            
            if status == 1:
                statusStr = 'Online'
            elif status == 0:
                statusStr = 'Offline'
            else:
                statusStr = 'Undefined'
                
           
            
            gPIO['Status'] = statusStr
            
                
            tempActivity = {
                    "Time": datetime.now().strftime("%d/%m/%Y %H:%M:%S:%f")[:-3],
                    "Activity": gPIO['Status']
                }
            
            # tempActivityArray.append(tempActivity)
            
            gpioLogUrl = os.path.join(logs_url, "GPIO" + str(gPIO['No']), "GPIO" + str(gPIO['No']) + "_" + datetime.now().strftime("%d-%m-%Y") + ".csv")
            
            with open(gpioLogUrl, 'a') as file:
                writer = csv.DictWriter(file, fieldnames=gPIO_header)
                tempArray = []
                tempArray.append(tempActivity)
                writer.writerows(tempArray)
                file.close()
                
            
            # if len(tempActivityArray) > 5:
            #     tempActivityArray.pop(0)
                
            # gPIO['Activities'] = tempActivityArray
                
            with open(json_url, 'w') as file:
                json.dump(availableGPIO, file, indent=4)
                
def checkStatus(indicator = None):
    
    while indicator == True:
        availableGPIO = json.load(open(json_url))
        for gPIO in availableGPIO['GPIOs']:
            currStatus = 1 if str(gPIO['Status']) == 'Online' else 0
            
            status = GPIO.input(int(gPIO['No']))
            
            if(int(status) != int(currStatus)):
                updateArray(int(gPIO['No']), status)
        
        time.sleep(0.25)
        
def updateData(channel):
    value = GPIO.input(channel)
    
    updateArray(channel, value)
 
def getserial():
  # Extract serial from cpuinfo file
  cpuserial = "0000000000000000"
  try:
    f = open('/proc/cpuinfo','r')
    for line in f:
      if line[0:6]=='Serial':
        cpuserial = line[10:26]
    f.close()
  except:
    cpuserial = "ERROR000000000"
 
  return cpuserial

def verify():
    availableData = json.load(open(json_url))
    storedRegkey = availableData['RegKey']
    
    serialno = getserial()
    generatedRegkey = encrypt(serialno, 'syt@1234')
    
    
    if "b'" + str(storedRegkey) + "'" == str(generatedRegkey):
        return True
    else:
        availableData['RegKey'] = ''
        with open(json_url, 'w') as file:
            json.dump(availableData, file, indent=4)

        return False
    
    
@app.route("/")
def splash():
    return redirect(url_for("login"))

    
@app.route("/Login/")
def login():
    userName = ''
    passWord = ''
            
    return render_template(
                        "login.html",
                        userName = userName,
                        passWord = passWord
                    )
        
@app.route("/Login/", methods=['POST'])
def verifyPi():
    if request.form['verifyPi'] == 'Submit':
        username = request.form['username']
        password = request.form['password']
        
        if username == 'admin' and password == 'admin':
            availableData = json.load(open(json_url))
            regKey = availableData['RegKey']
            
            if regKey == '':
                #For Registration
                return redirect(url_for("register"))
            else:
                #For Verification
                if verify() == True:
                    return redirect(url_for("dashboard")) 
                else:
                    return redirect(url_for("login"))
        else:
            return redirect(url_for("login"))

@app.route("/Register") 
def register():
    serialno = getserial()
    return render_template(
                    "register.html",
                    serialno = serialno
                )

@app.route("/Dashboard/")
def dashboard():
    availableGPIO = json.load(open(json_url))
    GPIO.cleanup()
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    for gPIO in availableGPIO['GPIOs']:
        if gPIO['Type'] == 'input':
            GPIO.setup(
                int(gPIO['No']), 
                GPIO.IN,
                pull_up_down=GPIO.PUD_DOWN
            )
            GPIO.add_event_detect(int(gPIO['No']), GPIO.BOTH, callback=updateData, bouncetime=10)
        else:
            GPIO.setup(
                int(gPIO['No']), 
                GPIO.OUT
            )
    
    return render_template(
                    "dashboard.html",
                    len = len(availableGPIO['GPIOs']),
                    gpios = availableGPIO['GPIOs']
                )

@app.route("/Dashboard/", methods=['POST'])
def dashboard_post():
    
    toggle = request.json.get('check')
    gpioNo = request.json.get('gpioNo')
    updateArray(gpioNo, toggle)
    
    availableGPIO = json.load(open(json_url))
    
    if toggle == 1:
        GPIO.output(int(gpioNo), GPIO.HIGH)
    if toggle == 0:
        GPIO.output(int(gpioNo), GPIO.LOW)
    
    return render_template(
            "dashboard.html",
            len = len(availableGPIO['GPIOs']),
            gpios = availableGPIO['GPIOs']
        )
    
@app.route("/download/<no>")
def download_Log(no = None):
    gpioNo      = no
    gpioLogUrl = os.path.join(logs_url, "GPIO" + str(gpioNo), "GPIO" + str(gpioNo) + "_" + datetime.now().strftime("%d-%m-%Y") + ".csv")
    return send_file(
        gpioLogUrl,
        as_attachment=True
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

@app.route("/Register/", methods=['POST'])
def registerPi():
    if request.form['registerPi'] == 'Submit':
        regkey = request.form['regkeyforverify']
        availableData = json.load(open(json_url))
        availableData['RegKey'] = regkey
        
        with open(json_url, 'w') as file:
            json.dump(availableData, file, indent=4)
            
        if verify() == True:
            return redirect(url_for("dashboard")) 
        else:
            return redirect(url_for("login"))
            
            


                
if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')
            
    