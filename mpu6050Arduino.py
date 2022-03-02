import kivy
from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.slider import Slider 
from kivy_garden.graph import Graph, MeshLinePlot
from kivy.clock import Clock
from kivy.properties import ObjectProperty
import serial
import numpy as np 
import struct
import time
import os
import serialMPU 
import copy
import csv
import datetime
import subAmortiguadoLibre


class Inicio(Widget):

    
    def __init__(self, **kwargs):
           
        # Configuracion de Elementos relacionados con la comunicación Serie
        self.maximos = []
        self.ultimo_grafico = []
        self.sensitivity = 2048 # conversion digital a G
        self.gravedad = 0 #constante para restar

        self.sampleRate = 1000 # SampleRate de Arduino
        self.fftSize = 2048 # Ventana para calcular la FFT
        self.AVERAGE = 2
        # Variables lógicas usadas 
        self.status = 0
        self.cuentaFFT = 0
        self.conectado = False
        self.modoForzadoOn = False
        self.graficosAmplitudDinamica = np.zeros(100)
        self.textosGraficosAmplitudDinamica = []
        # Armado de app Widget con vinculo con archivo de estilo cistas.kv
        # Acomodar
        self.t_max = 10 # Tiempo en segundos que se muestran 
        self.muestras_plot = self.t_max * self.sampleRate
        graph_wf = ObjectProperty(None)
        graph_sp = ObjectProperty(None)
        boton_on_libre = ObjectProperty(None)
        boton_on_forzado = ObjectProperty(None)
        slider = ObjectProperty(None)
        boton_velocidad = ObjectProperty(None)
        resetear = ObjectProperty(None)
        exportar = ObjectProperty(None)
        corregir = ObjectProperty(None)
        boton_conectar = ObjectProperty(None)
        texto_usuario = ObjectProperty(None)
        subir_velocidad = ObjectProperty(None)
        bajar_velocidad = ObjectProperty(None)
        guardar_maximo = ObjectProperty(None)
        calcular_parametros = ObjectProperty(None)
        texto_masa = ObjectProperty(None)
        super().__init__(**kwargs)

        # Graficos para el real_time
        self.plot_wf = MeshLinePlot(color=[1, 0.2, 0.3, 1])
        self.plot_sp = MeshLinePlot(color=[0.8, 0.6, 0.9, 1])
        self.plot_maximos = MeshLinePlot(color=[1, 0.2, 0.3, 1])
       
    def comunicacionArduino(self,tipo):
        # Rutina para sincronizar con Arduino, creada por FACUNDO RAMON en Processing y Adaptada a Python
        # Escribiendo una "r" el sistema arranca a transmitir
        # Escribiendo una "s" el sistema se detiene     
        # Escribiend un mensaje formado de "v+numero+_" el sistema incluye "numero" como velocidad del motor
        if tipo == "r":
            self.arduino.serialConnection.write(bytes("r", 'ascii'))
           
        elif tipo == "s":
            self.arduino.serialConnection.write(bytes("s", 'ascii'))

        elif tipo == "v":          
            self.arduino.serialConnection.write(bytes("v"+ str(self.velocidad)+"_", 'ascii'))


    def conectar(self):
       
        self.texto_usuario.text = ""
        if not self.conectado:

            # Defino parámetros para el objeto Serial
            # Leo variable de ambiente con el nombre del puerto
            portName = os.environ['ARDUINO_UNTREF']
            #portName = '/dev/cu.usbmodem101'
            baudRate = 115200
            dataNumBytes = 2        # number of bytes of 1 data point
            numPlots = 3            # number of plots in 1 graph
            self.arduino  = serialMPU.serialPlot(portName, baudRate, dataNumBytes, numPlots)   # initializes all required variables
            
            a = str(self.arduino.serialConnection.readline())
            if a[-9:-5] == "_OK_":
               
                self.texto_usuario.text = "Sync OK"
                self.texto_usuario.color = (0.1,1,0.1,1)
                self.boton_on_forzado.disabled = False
                self.boton_on_libre.disabled = False
                self.conectado = True
                self.boton_conectar.text = "Desconectar"
                self.boton_conectar.disabled = True
            else:
               
                self.texto_usuario.text = "Sync ERROR"
                self.texto_usuario.color = (1,0.1,0.1,1)
                self.arduino.serialConnection.close()
            
        else:
            self.conectado = False
            self.boton_conectar.text = "Conectar"
            self.arduino.close()
            self.boton_on_libre.disabled = True
            self.boton_on_forzado.disabled = True

    def pressedLibre(self): 
        i = self.status     
        if i == 1:
            self.status = 0
            # Acomodo botones
            self.boton_on_libre.text ="Estudio Libre"
            self.boton_conectar.disabled = False
            self.boton_on_forzado.disabled = False
            self.resetear.disabled = True
            self.exportar.disabled = True
            self.corregir.disabled = True
            self.subir_velocidad.disabled = True 
            self.bajar_velocidad.disabled = True 
            self.calcular_parametros.disabled = True
            # Detengo
            self.stop()
        else:
            self.status = 1
            # Acomodo botones
            self.boton_on_libre.text ="Detener"
            self.boton_conectar.disabled = True
            self.boton_on_forzado.disabled = True
            self.resetear.disabled = False
            self.exportar.disabled = False
            self.corregir.disabled = False
            self.subir_velocidad.disabled = True 
            self.bajar_velocidad.disabled = True 
            self.calcular_parametros.disabled = False
            # Inicio
            self.startLibre()      

    def pressedForzado(self): 
        i = self.status     
        if i == 1:
            self.status = 0
            # Acomodo botones

            self.boton_on_forzado.text ="Estudio Forzado"
            
            self.stop()
        else:
            self.status = 1
            # Acomodo botones
            self.boton_on_forzado.text ="Detener"
            self.corregir.disabled = False
            self.boton_velocidad.disabled = False
            self.boton_on_libre.disabled = True
            self.boton_conectar.disabled = False 
            self.subir_velocidad.disabled = False 
            self.bajar_velocidad.disabled = False 
            self.calcular_parametros.disabled = True 
            # Inicio

            self.startForzado()
               
    def startLibre(self):
        #Nombre para guardar como CSV
        self.nombreArchivo =  str(datetime.datetime.now()) + '- PruebaLibre'

        self.graph_wf.add_plot(self.plot_wf)
        self.graph_sp.add_plot(self.plot_sp)

        #Asigno coeficiente para filtrado 
        self.arduino.EMA_ALPHA = 0.05 
        self.comunicacionArduino("r")
        time.sleep(1)
        # Comienzo a ejecutar tarea en 2do plano
        self.arduino.readSerialStart()
        time.sleep(1)
        Clock.schedule_interval(self.modoLibre, 0.1)
        Clock.schedule_interval(self.modoForzado, 2*self.fftSize/self.sampleRate)
   
    def startForzado(self):
        self.modoForzadoOn = True
        self.nombreArchivo = str(datetime.datetime.now()) + '- PruebaForzado'
        
        self.graph_wf.add_plot(self.plot_wf)
        self.graph_sp.add_plot(self.plot_sp)

        #Arranco motor rapido para darle empuje
        self.velocidad = 120
        self.comunicacionArduino("v")

        #Asigno coeficiente para filtrado 
        self.arduino.EMA_ALPHA = 0.2 
        self.comunicacionArduino("r")
        time.sleep(0.5)

        #Bajo la velocidad del motor
        self.velocidad = int(self.slider.value)
        self.comunicacionArduino("v")

        # Comienzo a ejecutar tarea en 2do plano
        self.arduino.readSerialStart()
        # Comienzo a ejecutar la graficación 
        Clock.schedule_interval(self.modoForzado, 1.3*self.fftSize/self.sampleRate)
        Clock.schedule_interval(self.modoLibre, 0.1)
        
    def stop(self):
        self.resetearWF()
        self.exportCSV()
        self.comunicacionArduino("s")
        Clock.unschedule(self.modoForzado)
        Clock.unschedule(self.modoLibre)
        

    def resetearWF(self):
        # Vuelvo a cero la variable y ajusto los ejes
        self.gravedad = np.mean(np.array(self.arduino.valores))
        print('La constante gravitatoria es' + str(self.gravedad))

        self.arduino.valores = []
        self.arduino.vaores2 = []
        self.maximos = []
        self.maximosList = []
        
        self.cuentaFFT = 0

        self.graph_wf.xmin = 0
        self.graph_wf.xmax = self.t_max 
       
        self.graph_wf.add_plot(self.plot_wf)
        self.graph_sp.add_plot(self.plot_sp)
        self.plot_wf.points = []
        self.plot_sp.points = []
        
        

    def cambiarVelocidad(self):
        self.velocidad = int(self.slider.value)
        self.comunicacionArduino("v")

    def velocidadSubir(self):
        self.slider.value = self.slider.value + 1
        self.cambiarVelocidad()
        
    def velocidadBajar(self):
        self.slider.value = self.slider.value - 1
        self.cambiarVelocidad()

    def cambiarOrdenBits(self):
        self.arduino.corregir = 1

    def exportCSV(self):
        ofile  = open(self.nombreArchivo, "a")
        writer = csv.writer(ofile, delimiter=',')
        if not self.modoForzadoOn:
            for i in range(0,len(self.arduino.valores)):
                writer.writerow([self.arduino.valores[i]-self.gravedad])
            ofile.close()
        else:
            for i in range(0,len(self.maximosList)):
                writer.writerow([self.maximosList])
            ofile.close()
        print("Valores guardados en disco")

    def guardarMaximo(self):
        if self.maximos == []:
            self.maximos = np.zeros(len(self.ultimo_grafico))
        self.maximos = np.maximum(self.maximos , self.ultimo_grafico)
        self.maximosList = self.maximos.tolist()
        self.graph_sp.add_plot(self.plot_maximos)
        self.plot_maximos.points = [(i*(self.sampleRate/2)/self.fftSize, j) for i, j in enumerate(self.maximosList)]


    def modoLibre(self, dt):
        
        if len(self.arduino.valores) >= 65535: #Limite de valores que se pueden graficar en Kivy Garden Graph
            self.exportCSV()
            self.resetearWF()
            

        if len(self.arduino.valores) > self.graph_wf.xmax * self.sampleRate:
            # AJusto los ejes para permitir que avance el gráfico temporal
            self.graph_wf.xmin = self.t_max + self.graph_wf.xmin
            self.graph_wf.xmax = self.t_max + self.graph_wf.xmax
            self.graph_wf.add_plot(self.plot_wf)
            
        self.plot_wf.points = [(i/self.sampleRate, j - self.gravedad) for i, j in enumerate(self.arduino.valores)]
       
    
    def modoForzado(self,dt):
        
        if len(self.arduino.valores2)> self.fftSize: # ME aseguro que haya al menos esa cantidad de muestras antes de emepzar
            
            self.sp_data = np.array(self.arduino.valores2[self.fftSize*self.cuentaFFT:self.fftSize*(self.cuentaFFT+1)])
            
            if len(self.sp_data) == self.fftSize:
                
                self.sp_data = np.fft.fft(self.sp_data, n= self.fftSize)
                self.sp_data = np.abs(self.sp_data[0:int(self.fftSize/2)])


                # Promediado de FFT
                if self.cuentaFFT == 0: # Cuando es el primer elemento defino el array y concateno N veces
                    self.sp_data_avg = np.array([self.sp_data,]*self.AVERAGE)
                    #self.maximos = np.array([self.sp_data,]*30)
                else: # Luego empiezo a reemplazar columnas 
                    self.sp_data_avg = np.vstack([self.sp_data_avg[1:,:] , self.sp_data])
                
                self.cuentaFFT += 1 

                if self.cuentaFFT < self.AVERAGE:
                    self.plot_sp.points = [(i*(self.sampleRate/2)/self.fftSize, j/10) for i, j in enumerate(self.sp_data)]
                    self.ultimo_grafico =  self.sp_data/10
                else:
                    sp_data_av = self.sp_data_avg.sum(axis = 0)/self.AVERAGE
                    sp_data_av[0]=sp_data_av[1]
                    self.plot_sp.points = [(i*(self.sampleRate/2)/self.fftSize, j/10) for i, j in enumerate(sp_data_av)]
                    self.sp_data_av = sp_data_av
                    self.ultimo_grafico =  self.sp_data_av/10
            
    def calcularParam(self):
        self.masa = float(self.texto_masa.text)
        estado, grafico, texto = subAmortiguadoLibre.calculo(waveform = self.arduino.valores, fs = self.sampleRate, masa = self.masa, graficosPrevios = self.graficosAmplitudDinamica, stringPrevios= self.textosGraficosAmplitudDinamica)
        self.graficosAmplitudDinamica = np.vstack((self.graficosAmplitudDinamica,grafico))
        self.textosGraficosAmplitudDinamica.append(texto)
       

       # try:
       #     self.masa = float(self.texto_masa.text)
       #     estado, grafico = subamortiguadoModif.calculo(waveform = self.arduino.valores, fs = self.sampleRate, masa = self.masa, graficosPrevios = self.graficosAmplitudDinamica)
       #     self.graficosAmplitudDinamica = np.vstack((self.graficosAmplitudDinamica,grafico))
           
       ## except:
       #     print("La masa debe ser numérica")
            

        
class MPU6050ArduinoApp(App):

    def build(self):
        return Inicio()


if __name__ == '__main__':
    MPU6050ArduinoApp().run()