import numpy as np
import math
import scipy.integrate
import datetime
import threading


class Propellor(object):
    """docstring for Propellor."""
    def __init__(self, diameter, pitch):
        """docstring for the initializtion of the Propellor"""
        self.diameter = diameter
        self.pitch = pitch
        self.speed = 0 # RPM of the Propellor
        self.thrust = 0

    def setSpeed(self, speed):
        """docstring for setting the speed"""
        self.speed = speed
        ### The link below was used for thrust calculations, this is a
        ### simplified form, which will undershoot dynamic thrust and
        ### overshoot static thrust by ~ 15%-30%
        ### http://www.electricrcaircraftguy.com/2013/09/propeller-static-dynamic-thrust-equation.html
        self.thrust = 4.392e-8 * self.speed * math.pow(self.diameter,3.5)
        self.thrust = self.thrust / math.sqrt(self.pitch)
        self.thrust = self.thrust * (4.23e-4 * self.speed * self.pitch)
