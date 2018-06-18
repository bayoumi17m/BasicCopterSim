import numpy as np
import math
import scipy.integrate
import datetime
import threading


class Propellor(object):
    """
    This class controls a propellor for the copter class below
    Each instance of the propellor will rely on its physical parameters
    and thus will generate different thrusts or move at different speeds.

    Instance Attributes:
        diameter: The diameter of the propellor in inches [float or int]
        pitch: The pitch of the propellor in inches [float or int]
        speed: The RPM of the propellor at time t in rotation/min [float or int]
        thrust: The force generated by the propellor in Newtons [float or int]
    """
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


class Copter(object):
    """Abstract Class for Drones with Propellors"""
    def __init__(self, wings, num_wings, gravity = 9.81, b = 0.0245):
        self.wings = wings
        self.g = gravity
        self.b = b
        self.thread = None
        self.ode =  scipy.integrate.ode(self.state_dot).set_integrator('vode',
            nsteps=500,method='bdf')
        self.time = datetime.datetime.now()
        # Use a dictionary to store information about the Copters before init
        for key in self.wings:
            self.wings[key]['state'] = np.zeros(12)
            self.wings[key]['state'][0:3] = self.wings[key]['position']
            self.wings[key]['state'][6:9] = self.wings[key]['orientation']
            self.setupWings(key,num_wings)
            # From Quadrotor Dynamics and Control by Randal Beard
            ixx=((2*self.wings[key]['weight']*self.wings[key]['r']**2)/5)+ \
                (2*self.wings[key]['weight']*self.wings[key]['L']**2)
            iyy=ixx
            izz=((2*self.wings[key]['weight']*self.wings[key]['r']**2)/5)+ \
                (4*self.wings[key]['weight']*self.wings[key]['L']**2)
            self.wings[key]['I'] = np.array([[ixx,0,0],[0,iyy,0],[0,0,izz]])
            self.wings[key]['invI'] = np.linalg.inv(self.wings[key]['I'])
        self.run = True


    def setupWings(self,key,num_wings):
        for i in range(num_wings):
            self.wings[key]['m' + str(i+1)] = Propeller(
                self.wings[key]['prop_size'][0],self.wings[key]['prop_size'][1])


    def rotation_matrix(self,angles):
        ct = math.cos(angles[0])
        cp = math.cos(angles[1])
        cg = math.cos(angles[2])
        st = math.sin(angles[0])
        sp = math.sin(angles[1])
        sg = math.sin(angles[2])
        R_x = np.array([[1,0,0],[0,ct,-st],[0,st,ct]])
        R_y = np.array([[cp,0,sp],[0,1,0],[-sp,0,cp]])
        R_z = np.array([[cg,-sg,0],[sg,cg,0],[0,0,1]])
        R = np.dot(R_z, np.dot( R_y, R_x ))
        return R

    def wrap_angle(self,val):
        return( ( val + np.pi) % (2 * np.pi ) - np.pi )


    def state_dot(self, time, state, key):
        raise NotImplementedError()


    def update(self, dt):
        for key in self.wings:
            self.ode.set_initial_value(self.wings[key]['state'],
                0).set_f_params(key)
            self.wings[key]['state'] = self.ode.integrate(self.ode.t + dt)
            self.wings[key]['state'][6:9] = \
                self.wrap_angle(self.wings[key]['state'][6:9])
            self.wings[key]['state'][2] = max(0,self.wings[key]['state'][2])


    def set_motor_speeds(self,quad_name,speeds):
        for i in range(num_wings):
            self.wings[key]['m' + str(i+1)].set_speed(speeds[i])


    def get_position(self,quad_name):
        return self.wings[quad_name]['state'][0:3]


    def get_linear_rate(self,quad_name):
        return self.wings[quad_name]['state'][3:6]


    def get_orientation(self,quad_name):
        return self.wings[quad_name]['state'][6:9]


    def get_angular_rate(self,quad_name):
        return self.wings[quad_name]['state'][9:12]


    def get_state(self,quad_name):
        return self.wings[quad_name]['state']


    def set_position(self,quad_name,position):
        self.wings[quad_name]['state'][0:3] = position


    def set_orientation(self,quad_name,orientation):
        self.wings[quad_name]['state'][6:9] = orientation


    def get_time(self):
        return self.time


    def thread_run(self,dt,time_scaling):
        rate = time_scaling*dt
        last_update = self.time
        while(self.run==True):
            time.sleep(0)
            self.time = datetime.datetime.now()
            if (self.time-last_update).total_seconds() > rate:
                self.update(dt)
                last_update = self.time


    def start_thread(self,dt=0.002,time_scaling=1):
        self.thread_object = threading.Thread(target=self.thread_run,
            args=(dt,time_scaling))
        self.thread_object.start()


    def stop_thread(self):
        self.run = False


class Quadcopter(Copter):
    """docstring for Quadcopter."""
    def __init__(self, wings, gravity = 9.81, b = 0.0245):
        super().__init__(wings,4,gravity,b)

    def state_dot(self, time, state, key):
        state_dot = np.zeros(12)
        # The velocities(t+1 x_dots equal the t x_dots)
        state_dot[0] = self.wings[key]['state'][3]
        state_dot[1] = self.wings[key]['state'][4]
        state_dot[2] = self.wings[key]['state'][5]
        # The acceleration
        x_dotdot = np.array([0,0,-self.wings[key]['weight']*self.g]) + \
            np.dot(self.rotation_matrix(self.wings[key]['state'][6:9]),
            np.array([0,0,(self.wings[key]['m1'].thrust + \
            self.wings[key]['m2'].thrust + self.wings[key]['m3'].thrust + \
            self.wings[key]['m4'].thrust)]))/self.wings[key]['weight']
        state_dot[3] = x_dotdot[0]
        state_dot[4] = x_dotdot[1]
        state_dot[5] = x_dotdot[2]
        # The angular rates(t+1 theta_dots equal the t theta_dots)
        state_dot[6] = self.wings[key]['state'][9]
        state_dot[7] = self.wings[key]['state'][10]
        state_dot[8] = self.wings[key]['state'][11]
        # The angular accelerations
        omega = self.wings[key]['state'][9:12]
        tau = np.array([self.wings[key]['L']*(self.wings[key]['m1'].thrust- \
            self.wings[key]['m3'].thrust),
            self.wings[key]['L']*(self.wings[key]['m2'].thrust- \
            self.wings[key]['m4'].thrust),
            self.b*(self.wings[key]['m1'].thrust-self.wings[key]['m2'].thrust+ \
            self.wings[key]['m3'].thrust-self.wings[key]['m4'].thrust)])
        omega_dot = np.dot(self.wings[key]['invI'], (tau - np.cross(omega,
            np.dot(self.wings[key]['I'],omega))))
        state_dot[9] = omega_dot[0]
        state_dot[10] = omega_dot[1]
        state_dot[11] = omega_dot[2]
        return state_dot
