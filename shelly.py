#!/usr/bin/python3
# -*- coding: utf-8 -*-

from pyShelly import pyShelly
from pyShelly.const import INFO_VALUE_CONSUMPTION

from datetime import timedelta
import time
import os
import logging

class ShellyCommunicator(object):

    def __init__(self, shelly_ip, exit_after=False):
        self._shelly_ip = shelly_ip
        self._shelly = pyShelly()
        self._shelly.mdns_enabled = False # no discovery
        self._shelly._coap = None # no discovery

        self._shelly.update_status_interval = timedelta(seconds=60) # update every minute
        self._shelly.cb_device_added.append(self._device_added)

        self._shelly.add_device_by_ip(shelly_ip, None)
        
        # this is for the functions.
        self._method = None
        self._callback = None
        self._subid = None # may be powermeter or relay id
        
        self._exit_after = exit_after

    def _reset(self):
        logging.debug("resetting this shelly")
        self._method = None
        self._callback = None
        self._subid = None # may be powermeter or relay id
        if self._exit_after:
            os._exit(0)

    def _do(self):
        self._shelly.start()
        
    def _device_updated(self, device):
        text = 'update for device id: "{i}", device_type: "{t}", state: "{s}"'.format(i=device.id, t=device.device_type, s=device.state)
        logging.debug(text)
        
        if self._subid and device.id.endswith(self._subid):
            if device.device_type == "RELAY":
                if self._method == "turn_on":
                    device.turn_on()
                    if (self._callback):
                        self._callback()
                    self._reset()
                elif self._method == "turn_off":
                    device.turn_off()
                    if (self._callback):
                        self._callback()
                    self._reset()
                if self._method == "relay_state":
                    if (self._callback):
                        self._callback(device.state)
                        self._reset()
            elif device.device_type == "POWERMETER":
                if self._method == "power_consumption":
                    if (self._callback):
                        value = device.sensor_values[INFO_VALUE_CONSUMPTION]
                        self._callback(value)
                        self._reset()
        
    def _device_added(self, device, infos):
        # if not already updated
        already_added = list(filter(lambda dev: (dev.device_type == device.device_type and dev.id == device.id), device.cb_updated))
        if not already_added:
            device.cb_updated.append(self._device_updated)
            logging.debug("added device %s", device)
        
    def _action(self, method, id, callback):
        self._method = method
        self._subid = id
        self._callback = callback
        self._do()
        
    def turn_on(self, relay_id, callback=None):
        self._action("turn_on", relay_id, callback)
    
    def turn_off(self, relay_id, callback=None):
        self._action("turn_off", relay_id, callback)
        
    def relay_state(self, relay_id, callback):
        # callback receives one argument to be a bool
        self._action("relay_state", relay_id, callback)

    def power_consumption(self, powermeter_id, callback):
        # callback get's one argument that is a float
        self._action("power_consumption", powermeter_id, callback)
