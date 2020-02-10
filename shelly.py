#!/usr/bin/python3
# -*- coding: utf-8 -*-

from pyShelly import pyShelly
from pyShelly.const import INFO_VALUE_CURRENT_CONSUMPTION

from datetime import timedelta
import time
import os
import logging

class MethodRequest(object):
    
    def __init__(self, meth, subid, callback):
        self._method = meth
        self._callback = callback
        self._subid = subid # may be powermeter or relay id

class ShellyCommunicator(object):

    def __init__(self, shelly_ip, exit_after=False):
        '''
        
        exit_after if all the methodrequets are processed it will call os._exit()
        '''
        self._shelly_ip = shelly_ip
        self._shelly = pyShelly()
        self._shelly.mdns_enabled = False # no discovery
        self._shelly._coap = None # no discovery

        self._shelly.update_status_interval = timedelta(seconds=60) # update every minute
        self._shelly.cb_device_added.append(self._device_added)

        self._shelly.add_device_by_ip(shelly_ip, None)
        
        # this is for the functions.
        self._method_requests = []
        
        self._exit_after = exit_after
        self._started = False

    def reset(self):
        logging.debug("resetting this shelly")
        self._method_requests = []

    def do(self):
        if not self._started:
            self._shelly.start()
            self._started = True
        
    def _device_updated(self, device):
        text = 'update for device id: "{i}", device_type: "{t}", state: "{s}"'.format(i=device.id, t=device.device_type, s=device.state)
        logging.debug(text)

        hit_mr = None
        for mr in self._method_requests:
            if device.id.endswith(mr._subid):
                if device.device_type == "RELAY":
                    if mr._method == "turn_on":
                        device.turn_on()
                        if (mr._callback):
                            mr._callback()
                        hit_mr = mr
                    elif mr._method == "turn_off":
                        device.turn_off()
                        if (mr._callback):
                            mr._callback()
                        hit_mr = mr
                    elif mr._method == "relay_state":
                        if (mr._callback):
                            mr._callback(device.state)
                        hit_mr = mr
                elif device.device_type == "POWERMETER":        
                    if mr._method == "power_consumption":
                        if (mr._callback):
                            mr._callback(device.sensor_values[INFO_VALUE_CURRENT_CONSUMPTION])
                        hit_mr = mr
        if hit_mr:
            self._method_requests.remove(hit_mr)
            if self._exit_after and not self._method_requests:
                os._exit(0)
            
                
        
    def _device_added(self, device, infos):
        # if not already updated
        already_added = list(filter(lambda dev: (dev.device_type == device.device_type and dev.id == device.id), device.cb_updated))
        if not already_added:
            device.cb_updated.append(self._device_updated)
            logging.debug("added device %s", device)
    
    def _add_action(self, meth, subid, callback):
        mr = MethodRequest(meth, subid, callback)
        self._method_requests.append(mr)
        
    def turn_on(self, relay_id, callback=None):
        self._add_action("turn_on", relay_id, callback)
    
    def turn_off(self, relay_id, callback=None):
        self._add_action("turn_off", relay_id, callback)
        
    def relay_state(self, relay_id, callback):
        # callback receives one argument to be a bool
        self._add_action("relay_state", relay_id, callback)

    def power_consumption(self, powermeter_id, callback):
        # callback get's one argument that is a float
        self._add_action("power_consumption", powermeter_id, callback)
