 
from threading import Thread
import serial
import time
import collections
import struct
import copy
import os
import numpy as np
  
class serialPlot:
    def __init__(self, serialPort='/dev/ttyACM0', serialBaud=38400, dataNumBytes=2, numPlots=1, rango=2, sensibilidad = 2**16):
        # Filtado exponencial
        self.EMA_LP = 0 # Valor inicial del filtrado
        self.EMA_LP2 = 0 # Valor inicial del filtrado
        self.EMA_LP3 = 0 # Valor inicial del filtrado
        self.EMA_ALPHA = 0.9 # Coeficiente para el filtro 
        
        self.corregir = 0
        self.port = serialPort
        self.baud = serialBaud
        self.dataNumBytes = dataNumBytes
        self.numPlots = numPlots
        self.rango = rango
        self.sensibilidad = sensibilidad
        self.rawData = bytearray(dataNumBytes)
        self.rawData2 = bytearray(dataNumBytes)
        self.rawData3 = bytearray(dataNumBytes)
        self.dataType = None
        if dataNumBytes == 2:
            self.dataType = 'h'     # 2 byte integer
        elif dataNumBytes == 4:
            self.dataType = 'f'     # 4 byte float
        self.data = []
       
        self.isRun = True
        self.isReceiving = False
        self.thread = None
        self.plotTimer = 0
        self.previousTimer = 0
      
        print('Trying to connect to: ' + str(serialPort) + ' at ' + str(serialBaud) + ' BAUD.')
        try:
            os.system('echo 8323 | sudo -S chmod a+rw /dev/ttyACM0')
            self.serialConnection = serial.Serial(serialPort, serialBaud, timeout=4)
            print('Connected to ' + str(serialPort) + ' at ' + str(serialBaud) + ' BAUD.')
        except:
            print("Failed to connect with " + str(serialPort) + ' at ' + str(serialBaud) + ' BAUD.')
 
    def readSerialStart(self):
        
        if self.thread == None:
            self.valores=[]
            self.valores2=[]
            self.thread = Thread(target=self.backgroundThread)
            self.thread.start()
            # Block till we start receiving values
            while self.isReceiving != True:
                time.sleep(0.1)
        else:
            a = 1
 

    def backgroundThread(self):    # retrieve data
        time.sleep(1.0)  # give some buffer time for retrieving data
        self.serialConnection.reset_input_buffer()
        
        angYgir_prev = 0
        while (self.isRun):
            self.serialConnection.readinto(self.rawData)
            self.serialConnection.readinto(self.rawData2)
            self.serialConnection.readinto(self.rawData3)
            if self.corregir == 1:
                self.serialConnection.read(1)
                print("Corrigiendo Sincronización")
                self.corregir = 0
            else:
                # Convertir a float desde bytes
                dataFloat = float(struct.unpack('h', self.rawData)[0]*self.rango/self.sensibilidad) # Aceleración en X
                dataFloat2 = float(struct.unpack('h', self.rawData2)[0]*self.rango/self.sensibilidad) # Aceleración en Z
                dataFloat3 = float(struct.unpack('h', self.rawData3)[0]/131) # Velocidad Angular en Y
                # Filtrado Exponencial
                self.dataFiltada = self.EMA_ALPHA * dataFloat + (1 - self.EMA_ALPHA) * self.EMA_LP
                self.dataFiltada2 = self.EMA_ALPHA * dataFloat2 + (1 - self.EMA_ALPHA) * self.EMA_LP2
                self.dataFiltada3 = self.EMA_ALPHA * dataFloat3 + (1 - self.EMA_ALPHA) * self.EMA_LP3
                self.EMA_LP = self.dataFiltada 
                self.EMA_LP2 = self.dataFiltada3 
                self.EMA_LP3 = self.dataFiltada2 
                # Agregar valores de aceleración en x al vector general
                self.valores.append(self.dataFiltada)
                
                if dataFloat == 0:
                    dataFloat = 0.000001
                if dataFloat2 == 0:
                    dataFloat2 = 0.000001
                if dataFloat3 == 0:
                    dataFloat3 = 0.000001        
                # Cálculo del ángulo de inclinación por medio de filtro complementario
                # Tomado (para arduino) de: https://www.luisllamas.es/medir-la-inclinacion-imu-arduino-filtro-complementario/
                # y de: https://www.luisllamas.es/arduino-orientacion-imu-mpu-6050/
                angYacc = np.arctan(dataFloat2/dataFloat) * (180 / np.pi)
                #self.valores.append(angYacc)
                
                
                t0 = time.time()
                dt = time.time() - t0
                angYgir = self.dataFiltada3 * dt + angYgir_prev
                angYgir_prev = angYgir
                t0 = dt

                # Filtro Complementario
                angYtotal = 0.98 * angYgir + 0.02 * angYacc
                x = np.tan(angYtotal) * 0.8
                #print(angYtotal)
                self.valores2.append(self.dataFiltada3)
                self.isReceiving = True    

 
    def close(self):
        self.isRun = False
        self.thread.join()
        self.serialConnection.close()
        print('Disconnected...')

