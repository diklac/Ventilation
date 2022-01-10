# -*- coding: utf-8 -*-
"""
Created on Sat Jan  8 12:55:43 2022

@author: dikla
"""

import serial
from datetime import datetime as dt
import csv
import re
import signal
import matplotlib.pyplot as plt
import pandas as pd
import sys


DEF_COM_PORT = 'COM3'
DEF_BAUD_RATE = 115200
DEF_OUTPUT_FILE = 'sensor_output'
TIME_FMT = '%Y%m%d_%H_%M_%S'
USAGE_MSG = 'Usage: %s <read_serial | plot>\r\nFor read_serial, optional arguments: <com_port> <baud_rate> <output_file_name> <num row dump>\r\nFor plot, optional argument: <file_name>'
SERIAL_REGEX_PARSER = r'Temperature: ([0-9.]+)|Relative Humidity: ([0-9.]+)|CO2: ([0-9.]+)'
DEF_ROWS_NUM_DUMP = 10

    
    
class Application(object):
    '''
    A class for running an app in
    '''
    def __init__(self):
        signal.signal(signal.SIGINT, lambda signal, frame: self._signal_handler())
        self.terminated = False
        
    def _signal_handler(self):
        '''
        Update the inner state to terminated.
        '''
        self.terminated = True
        
    def Run(self):
        '''
        This is the application that runs while no signal is sent.        
        '''
        
class SerialReader(Application):
    '''
    data_dict has keys: Time, Temperature, CO2
    '''
    def __init__(self):
        super(SerialReader, self).__init__()
        self.serial_regex_parser = SERIAL_REGEX_PARSER
        self.display_items = ['Temperature', 'CO2']
        self.log_items = ['Time', 'Temperature', 'CO2']
        self.units = {'Time' : None, 'Temperature' : 'deg C', 'CO2' : 'ppm'}

    def parse_data(self, s, data_dict=None):
        '''
        build data_dict from line read from serial port
        '''
        if data_dict is None:
            data_dict = {}
        m = re.search(self.serial_regex_parser, s)
        if m:
            # temp
            if m.group(1):
                data_dict['Temperature'] = float(m.group(1))
            # humidity
            if m.group(2):
                data_dict['Relative Humidity'] = float(m.group(2))
            # CO2
            if m.group(3):
                data_dict['CO2'] = float(m.group(3))
        return data_dict
    
    def DisplayDict(self, data_dict):
        '''
        print the items in data_dict that are specified by object's display_items
        '''
        l = ['%s : %.2f %s' % (d, data_dict[d], self.units[d]) for d in data_dict.keys() if d in self.display_items]
        s = '\n'.join(l)
        if len(s) > 0:
            s = '--------\n' + s
        else:
            s = ''
        return s
    
    def GetFileName(self, prefix):
        '''
        get the standard file name using prefix: <prefix>_<time>.csv
        '''
        now = dt.now()
        time_str = now.strftime(TIME_FMT)
        output_file_name = prefix + '_' + time_str + '.csv'
        return output_file_name
    
    def AllDataGathered(self, data_dict):
        '''
        Return True if data_dict contains all the items specified in object's log_items
        '''
        gathered_data = list(data_dict.keys()) + ['Time']
        if set(self.log_items) <= set(gathered_data):
            return True
        else:
            return False
                
    
    def Run(self, com_port=DEF_COM_PORT, baud_rate=DEF_BAUD_RATE, output_file_name=DEF_OUTPUT_FILE, rows_num_dump=DEF_ROWS_NUM_DUMP):
        
        # open file to write to
        output_file_name = self.GetFileName(output_file_name)
        output_file = open(output_file_name, 'w', newline='')
        
        # create writer object and write the header
        writer = csv.writer(output_file)
        header = ['%s [%s]' % (l, self.units[l]) if self.units[l] else '%s' % (l) for l in self.log_items]
        writer.writerow(header)
        print('Opened CSV file %s' % output_file_name)
        
        # open serial port
        try:
            ser = serial.Serial(com_port, baud_rate)
        except serial.serialutil.SerialException:
            print('Error: Cannot open serial port %s.' % com_port)
            return
        print('Connected to serial port %s\n' % ser.name)
        
        # loop on reading
        data_dict = {}
        rows_counter = 0
        while not self.terminated:
            
            # parse data:
            # we gathered all the lines in this set
            if self.AllDataGathered(data_dict):
                # display
                print(self.DisplayDict(data_dict))
                
                # get time
                now = dt.now()
                time_str = now.strftime(TIME_FMT)
                data_dict['Time'] = time_str
                
                # write to file
                row = [data_dict[d] for d in self.log_items]
                writer.writerow(row)
                            
            # gather more lines
            line = ser.readline()
            rows_counter += 1
            data_dict = self.parse_data(str(line, 'utf-8'), data_dict)
            
            # if we collected enough rows, dump to file to mitigate lost data
            if rows_counter >= rows_num_dump:
                rows_counter = 0
                output_file.flush()
                       
        # cleanup
        ser.close()
        print('Finished reading from serial.')
        output_file.close()
        print('Closed output file %s.' % output_file_name)
        return output_file_name
 

class DataPlotter(object):
    def __init__(self):
        pass
        
    def LoadData(self, data_file_name=DEF_OUTPUT_FILE):
        
        # open data file and set csv reader
        #data_file = open(data_file_name)
        #data_reader = csv.reader(data_file)
        
        df = pd.read_csv(data_file_name)
        
        '''
        # read first row to get column names
        header = data_reader.next()
        
        # set data dictionary
        data = dict((k, 0) for k in header)
        
        # read data
        for row in data_reader:
            data.append(row)
            
        print(data)
        
        
        # close data file
        data_file.close()
        '''
        return df
        
    def PlotFile(self, data_file_name=DEF_OUTPUT_FILE):
        #fig, ax = plt.subplots()
        fig = plt.figure()
        
        # get data
        df = self.LoadData(data_file_name)
        curve_names = [k for k in df.keys() if k != 'Time']
        num_curves = len(curve_names)
        
        # parse time
        time = pd.to_datetime(df['Time'], format=TIME_FMT)        
        
        for ii in range(num_curves):
            
            plt.subplot(num_curves, 1, ii + 1)
            name = curve_names[ii]
            plt.plot(time, df[name], label = name)
            plt.grid()
            plt.xlabel('Time')
            plt.ylabel(name)
        
        plt.show()           

    
# run from cmd
if __name__ == '__main__':
    
    # no arguments, display usage
    if len(sys.argv) == 1:
        print(USAGE_MSG % sys.argv[0])
        exit()
    # at least one arguments
    else:
        purpose = sys.argv[1]
        # run to log serial port
        if purpose == 'read_serial':
            serial_reader = SerialReader()
            serial_reader.Run(*sys.argv[2:])
            exit()
        # run to plot data
        elif purpose == 'plot':
            dp = DataPlotter()
            dp.PlotFile(*sys.argv[2:])
            exit()
        else:
            print('Unknown purpose (first argument). Can be read_serial or plot.')
            exit()            
    
