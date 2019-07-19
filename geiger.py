#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""

BROKEN PYTHON3 PORT! FIX IT LOL

geiger_basic.py - to collect data from Geiger Counter 'GQ GMC-300E plus' with option to log data

using serial communication via /dev/gqgmc (linked to /dev/ttyUSB0 )
"""

# usage: /path/to/geiger_basic.py
#
# device command coding taken from:  https://sourceforge.net/projects/gqgmc/
#
# To avoid having to run a script as root (required for write access to USB) it is suggested
# to define a udev rule. Then the script can be used as a regular user:
#
# As root create a file '52-gqgmc.rules' in '/etc/udev/rules.d' with this content:
#    
#   SUBSYSTEM=="usb", ATTR{idVendor}=="1a86", ATTRS{idProduct}=="7523", MODE:="666", GROUP="plugdev"
#   SUBSYSTEM=="tty", KERNEL=="ttyUSB*", ATTRS{idVendor}=="1a86", MODE:="666", SYMLINK+="gqgmc"
#
# then do "sudo udevadm control --reload-rules" or restart your computer
# then unplug and replug your device
# this works on  Ubuntu Mate 16.04.01 with kernel 4.4.0-57-generic


__author__      = "ullix"
__copyright__   = "Copyright 2016"
__credits__     = ["Phil Gillaspy"]
__license__     = "GPL"
__version__     = "0.0.1"
__maintainer__  = ""
__email__       = ""
__status__      = "Development"


import sys
import serial
import time
import requests
import json


def stime():
    return time.strftime("%d.%m.%Y %H:%M:%S")


def getVER(ser):
    # send <GETVER>> and read 14 bytes as ASCII
    # my device: GQ GMC-300E plus

    ser.write(b'<GETVER>>') 
    return ser.read(14)


def getSERIAL(ser):
    # send <GETSERIAL>> and read 7 bytes
    # my device: F488007E05DDB8
    
    hexlookup = "0123456789ABCDEF"

    ser.write(b'<GETSERIAL>>')
    a = ser.read(7)
    
    rec =""
    for i in range(0,len(a)):    
        a1 = ((ord(a[i]) & 0xF0) >>4)
        a2 = ((ord(a[i]) & 0x0F))
        rec += hexlookup[a1] + hexlookup[a2]
        
    return rec


def getCFG(ser):
    # send <GETCFG>> and read 256 bytes

    ser.write(b'<GETCFG>>')
    cfgbytes = ser.read(256)
    cfg = []
    for i in range(0,len(cfgbytes)):
        cfg.append(ord(cfgbytes[i]))
    
    return cfg


def getDATETIME(ser):
    # send <GETDATETIME>> and read 7 bytes; convert from [YY][MM][DD][hh][mm][ss][AA] to date & time

    ser.write(b'<GETDATETIME>>')
    dt = ser.read(7)

    return str(ord(dt[2]))+"."+str(ord(dt[1]))+".20"+str(ord(dt[0]))+" "+str(ord(dt[3]))+":"+str(ord(dt[4]))+":"+str(ord(dt[5]))


def getVOLT(ser):
    # send <GETVOLT>> and read 1 byte
    # Voltage is equal to B converted to real number divided by 10.0, for example, B = 0x62 converts to 9.8V

    ser.write(b'<GETVOLT>>')
    
    return ord(ser.read(1))/10.


def getCPM(ser):
    # send <GETCPM>> and read 2 bytes; interpret as MSB and LSB

    ser.write(b'<GETCPM>>')
    rec = ser.read(2)
    return ord(rec[0])<< 8 | ord(rec[1])


def logCPM(ser, logflag = True):
    # getCPM 
    # if logflag is True then store CPM in log file with time stamp
    # return CPM

    cpm = getCPM(ser)

    if (logflag):
        log = open("./cpm.log", "a")   
        log.write(stime() + ", " + str(cpm) + "\n")
        log.close
        
    return cpm


def getTEMP(ser):
    # Firmware supported: GMC-320 Re.3.01 or later
    # send <GETTEMP>> and read 4 bytes
    # Return: Four bytes celsius degree data in hexdecimal: BYTE1,BYTE2,BYTE3,BYTE4
	# Here: BYTE1 is the integer part of the temperature.
	#       BYTE2 is the decimal part of the temperature.
	#       BYTE3 is the negative signe if it is not 0.  If this byte is 0, the then current temperture is greater than 0, otherwise the temperature is below 0.
	#       BYTE4 always 0xAA
    
    ser.write(b'<GETTEMP>>')
    rec = ser.read(4)

    return rec
    

def getGYRO(ser):
    # Firmware supported: GMC-320 Re.3.01 or later
    # Send <GETGYRO>> and read 7 bytes
    # Return: Seven bytes gyroscope data in hexdecimal: BYTE1,BYTE2,BYTE3,BYTE4,BYTE5,BYTE6,BYTE7
	# Here: BYTE1,BYTE2 are the X position data in 16 bits value. The first byte is MSB byte data and second byte is LSB byte data.
	#       BYTE3,BYTE4 are the Y position data in 16 bits value. The first byte is MSB byte data and second byte is LSB byte data.
	#       BYTE5,BYTE6 are the Z position data in 16 bits value. The first byte is MSB byte data and second byte is LSB byte data.
	#       BYTE7 always 0xAA
    
    ser.write(b'<GETGYRO>>')
    rec = ser.read(7)

    return rec

def postCPM(cpm):
    url = "http://ultrablast.local:3000/readings.json"
    dat = {'reading' : {'cpm' : cpm}} 
    headers = {'Content-Type' : 'application/json'}
    r = requests.post(url, data=json.dumps(dat), headers=headers)
    print("posting cpm: ", json.dumps(dat))
    
device = "GQ GMC-300E plus"

print("The device is: \t\t\t", device)

# open the serial port !!! NOTE: baud rate must be set at device first, default is 57600 !!!
ser = serial.Serial('/dev/gqgmc', 115200)
print("The device is at serial port:\t", ser.name)
#print "with these settings: \t\t",         
print(ser)

# print the version number
print("The firmware version is : \t",)
print(getVER(ser))

# print the serial number of the device
print("The serial number is :   \t",)
print(getSERIAL(ser))

# print the configuration
print("The configuration is (byte-number:value):   \t")
mycfg= getCFG(ser)
for i in range(0,16):
    print("\t\t\t\t",)
    for j in range(0,16):
        k = i*16+j
        print("%3d:%3d  " % (k, mycfg[k]),)
    print("")
    
# print Date and Time
print("Date and Time from device is:\t",)
print(getDATETIME(ser))

# Print Voltage 
print("Voltage of battery is:\t\t",)
print(getVOLT(ser))

# Print Temperature
print("Temperature of device is: \t",)
rec = getTEMP(ser)
for i in range(0,4):
    print(ord(rec[i]),)
print("")
    
# Print Gyro
print("Gyro data of device is: \t",)
rec = getGYRO(ser)
for i in range(0,7):
    print(ord(rec[i]),)
print("")

# Print (and log) the CPM every X seconds; logging optional
seconds = 5.1
print("The CPM every %5.2f sec:   \t" % (seconds))
# set logflag = True to print and log data; False to only print data
logflag = False
#logflag = False
try:
    while True:
        cpm = logCPM(ser, logflag)
        print(cpm)
        try:
          postCPM(cpm)
        except:
          pass
        time.sleep(seconds)
except KeyboardInterrupt:
    pass

ser.close()             # close port
