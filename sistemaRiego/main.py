import tkinter as tk
from asyncio import timeout
from datetime import datetime
from tkinter import ttk, mainloop
import numpy as np
import time
import threading
import socket
import matplotlib.pyplot as plt
from fontTools.merge.util import current_time
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from collections import deque

from matplotlib.ft2font import HORIZONTAL

from datetime import datetime
import matplotlib.dates as mdates

class esp32Interfaz:

    def __init__(self,master):
        self.n_temperaturas = 3
        self.n_humedades = 2
        self.n_ldr = 1
        self.master = master
        self.maxdatapoints=100


        self.temperaturas={f'T{i+1}':deque(maxlen=self.maxdatapoints)for i in range(self.n_temperaturas)}
        self.humedades={f'H{i + 1}':deque(maxlen=self.maxdatapoints) for i in range(self.n_humedades)}
        self.luminosidad={f'L{i + 1}':deque(maxlen=self.maxdatapoints) for i in range(self.n_ldr)}

        self.estadoTemperaturas={f'T{i+1}':False for i in range(self.n_temperaturas)}
        self.estadoHumedades={f'H{i + 1}':False for i in range(self.n_humedades)}
        self.estadoLuminosidad={f'L{i + 1}':False for i in range(self.n_ldr)}

        self.rangoTemperaturas={f'T{i+1}':False for i in range(self.n_temperaturas)}
        self.rangoHumedades={f'H{i + 1}':False for i in range(self.n_humedades)}
        self.rangoLuminosidad={f'L{i + 1}':False for i in range(self.n_ldr)}

        self.timestamps=deque(maxlen=self.maxdatapoints)

        mainFrame=ttk.PanedWindow(self.master,orient=tk.HORIZONTAL)
        mainFrame.pack(fill=tk.BOTH,expand=True)
        leftFrame=ttk.Frame(mainFrame)
        mainFrame.add(leftFrame)

        master.title("Interfaz Esp32")
        self.client_socket=None
        self.connected=False
        self.autoscroll=True
        # Crear parte visible
        connectionFrame=ttk.LabelFrame(leftFrame,text="Conexión WIFI")
        connectionFrame.pack(padx=10,pady=10,fill='x')
        ttk.Label(connectionFrame,text="IP:").grid(row=0,column=0,padx=5,pady=5)
        self.ipEntrada=ttk.Entry(connectionFrame)
        self.ipEntrada.grid(row=0,column=1,padx=5,pady=5)
        self.ipEntrada.insert(0,"10.0.0.6")

        ttk.Label(connectionFrame, text="Puerto:").grid(row=0, column=2, padx=5, pady=5)
        self.puertoEntrada=ttk.Entry(connectionFrame)
        self.puertoEntrada.grid(row=0, column=3, padx=5, pady=5)
        self.puertoEntrada.insert(0, "80")

        self.buttomConnect=ttk.Button(connectionFrame,text="Conectar", command=self.establecerConexion)
        self.buttomConnect.grid(row=0, column=4, padx=5, pady=5)

        # Frame para el slicer
        timeControlFrame = ttk.LabelFrame(leftFrame,text="Control de tiempo")
        timeControlFrame.pack(padx=10,pady=5,fill='x')

        ttk.Label(timeControlFrame,text="Tiempo (%): ").pack(side=tk.LEFT,padx=5)

        self.timeWindowScale = ttk.Scale(timeControlFrame,from_=1,to=100,orient=tk.HORIZONTAL)
        self.timeWindowScale.set(100)
        self.timeWindowScale.pack(side=tk.LEFT,fill='x',expand=True,padx=5)

        self.timeWindowScale.bind("<Motion>",self.updateTimeWindow)

        # Frame de notificaciones
        notificationFrame = ttk.LabelFrame(leftFrame, text="Notificaciones Wi-Fi")
        notificationFrame.pack(padx=10, pady=10, fill="both", expand=True)
        self.textoNotification=tk.Text(notificationFrame,wrap=tk.WORD,width=60,height=20)
        self.textoNotification.pack(side=tk.LEFT,fill="both",expand=True)

        scrollNotificationBar=ttk.Scrollbar(notificationFrame,orient="vertical",command=self.textoNotification.yview)
        scrollNotificationBar.pack(side=tk.RIGHT, fill="y")
        self.textoNotification.config(yscrollcommand=scrollNotificationBar.set)

        # Frame de consola
        consoleFrame=ttk.LabelFrame(leftFrame, text="Consola")
        consoleFrame.pack(padx=10,pady=10,fill="both",expand=True)
        self.textoConsola=tk.Text(consoleFrame,wrap=tk.WORD,width=60,height=20)
        self.textoConsola.pack(side=tk.LEFT,fill="both",expand=True)

        scrollBar=ttk.Scrollbar(consoleFrame,orient="vertical",command=self.textoConsola.yview)
        scrollBar.pack(side=tk.RIGHT, fill="y")
        self.textoConsola.config(yscrollcommand=scrollBar.set)

        cmdFrame = ttk.Frame(leftFrame)
        cmdFrame.pack(padx=10,pady=10,fill="x")
        self.cmdEntry=ttk.Entry(cmdFrame,width=50)
        self.cmdEntry.pack(side=tk.LEFT,padx=(0,5))
        self.cmdEntry.bind("<Return>",self.sendcommand)
        self.sendButton=ttk.Button(cmdFrame,text="Enviar",command=self.sendcommand)
        self.sendButton.pack(side=tk.LEFT)

        self.autoscrollvar=tk.BooleanVar(value=True)
        self.autoscrollcheck=ttk.Checkbutton(leftFrame,text="AutoScroll",variable=self.autoscrollvar,command=self.toggleAutoScroll)
        self.autoscrollcheck.pack(pady=5)
        rightFrame=tk.Frame(self.master)
        mainFrame.add(rightFrame)
        #rightFrame.grid(row=0,column=1,sticky="nsew")
        self.createPlot(rightFrame)
        self.hiloDeRecepcion=None

    def updateTimeWindow (self,event=None):

        if len(self.timestamps) > 0:
            porcentaje = self.timeWindowScale.get()
            windowSize = int(len(self.timestamps)*(porcentaje/100))

            if windowSize < 2:
                windowSize = 2
            start_idx = max(0,len(self.timestamps)-windowSize)
            times = list(self.timestamps)[start_idx:]
            x_dates = [datetime.fromtimestamp(t) for t in times]

            for i,line in enumerate(self.tempLines):
                y_data = list(self.temperaturas[f'T{i+1}'])[start_idx:]
                line.set_data(x_dates,y_data)

            for i, line in enumerate(self.humeLines):
                y_data = list(self.humedades[f'H{i + 1}'])[start_idx:]
                line.set_data(x_dates, y_data)

            for i, line in enumerate(self.ldrLines):
                y_data = list(self.luminosidad[f'L{i + 1}'])[start_idx:]
                line.set_data(x_dates, y_data)

            for ax in (self.ax1,self.ax2,self.ax3):
                ax.relim()
                ax.autoscale_view()
            self.canvas.draw()


    def createPlot(self,parent):
        self.figure,(self.ax1,self.ax2,self.ax3)=plt.subplots(3,1,figsize=(8,12))
        self.canvas=FigureCanvasTkAgg(self.figure,master=parent)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side=tk.TOP,fill=tk.BOTH,expand=1)
        self.ax1.set_title('Temperatura')
        self.ax2.set_title('Humedad')
        self.ax3.set_title('Luminocidad')


        self.tempLines=[self.ax1.plot([],[],label=f'T{i+1}')[0] for i in range(self.n_temperaturas)]
        self.humeLines = [self.ax2.plot([], [], label=f'H{i + 1}')[0] for i in range(self.n_humedades)]
        self.ldrLines = [self.ax3.plot([], [], label=f'L{i + 1}')[0] for i in range(self.n_ldr)]

        for ax in (self.ax1,self.ax2,self.ax3):
            ax.legend()
            #ax.set_xlim(0,100)
            #ax.set_ylim(0,100)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
            ax.grid(True)

        #self.figure.autofmt_xdate()


        self.figure.tight_layout()

    def procesarDatos(self,data):
        try:
            values=data.split(',')
            if len(values) != self.n_temperaturas + self.n_humedades + self.n_ldr:
                self.textoNotification.insert(tk.END,data + '\n')
                #self.textoConsola.insert(tk.END,"Número incorrecto de valores recibidos")
                raise ValueError("Número incorrecto de valores recibidos")

            current_time = time.time()
            self.timestamps.append(current_time)

            for i in range(self.n_temperaturas):
                tempValue=float(values[i])
                self.temperaturas[f'T{i+1}'].append(tempValue)

                if (tempValue < 0):
                    if not self.estadoTemperaturas[f'T{i+1}']:
                        self.textoNotification.insert(tk.END,f'Sensor T{i+1} sin conexión \n')
                        self.estadoTemperaturas[f'T{i+1}']=True

                else:
                    if self.estadoTemperaturas[f'T{i+1}']:
                        self.textoNotification.insert(tk.END, f'Sensor T{i+1} reconectado... \n')
                        self.estadoTemperaturas[f'T{i+1}']=False
                    elif tempValue < 10:
                        if not self.rangoTemperaturas[f'T{i + 1}']:
                            self.textoNotification.insert(tk.END,
                                                          f'Sensor T{i + 1} germinado congelandose: {tempValue} C \n')
                            self.rangoTemperaturas[f'T{i + 1}'] = True

                    elif tempValue > 35:
                        if not self.rangoTemperaturas[f'T{i + 1}']:
                            self.textoNotification.insert(tk.END,
                                                          f'Sensor T{i + 1} germinado alta temperatura: {tempValue} C \n')
                            self.rangoTemperaturas[f'T{i + 1}'] = True
                    else:
                        if self.rangoTemperaturas[f'T{i + 1}']:
                            self.textoNotification.insert(tk.END,
                                                          f'Sensor T{i + 1} temperatura en rango aceptable: {tempValue} C \n')
                            self.rangoTemperaturas[f'T{i + 1}'] = False

            for i in range(self.n_humedades):
                humedValue = float(values[i+self.n_temperaturas])
                self.humedades[f'H{i+1}'].append(humedValue)

                if (humedValue > 100):
                    if not self.estadoHumedades[f'H{i+1}']:
                        self.textoNotification.insert(tk.END,f'Sensor H{i+1} sin conexión \n')
                        self.estadoHumedades[f'H{i+1}']=True

                else:
                    if self.estadoHumedades[f'H{i+1}']:
                        self.textoNotification.insert(tk.END, f'Sensor H{i+1} reconectado \n')
                        self.estadoHumedades[f'H{i+1}']=False

                    elif humedValue < 20:
                        if not self.rangoHumedades[f'H{i+1}']:
                            self.textoNotification.insert(tk.END,f'Sensor H{i+1} ambiente seco: {humedValue} % \n')
                            self.rangoHumedades[f'H{i+1}']=True
                    else:
                        if self.rangoHumedades[f'H{i+1}']:
                            self.textoNotification.insert(tk.END,f'Sensor H{i+1} ambiente moderado: {humedValue} % \n')
                            self.rangoHumedades[f'H{i+1}']=False

            for i in range(self.n_ldr):
                ldrValue = float(values[i+self.n_temperaturas+self.n_humedades])
                self.luminosidad[f'L{i+1}'].append(ldrValue)

                if (ldrValue > 100):
                    if not self.estadoLuminosidad[f'L{i+1}']:
                        self.textoNotification.insert(tk.END,f'Sensor L{i+1} sin conexión \n')
                        self.estadoLuminosidad[f'L{i+1}']=True

                else:
                    if self.estadoLuminosidad[f'L{i+1}']:
                        self.textoNotification.insert(tk.END, f'Sensor L{i+1} reconectado \n')
                        self.estadoLuminosidad[f'L{i+1}']=False

                    elif ldrValue < 20:
                        if not self.rangoLuminosidad[f'L{i+1}']:
                            self.textoNotification.insert(tk.END,f'Sensor L{i+1} ambiente oscuro: {ldrValue} % \n')
                            self.rangoLuminosidad[f'L{i+1}']=True

                    elif ldrValue > 90:
                        if not self.rangoLuminosidad[f'L{i + 1}']:
                            self.textoNotification.insert(tk.END, f'Sensor L{i + 1} ambiente muy luminoso: {ldrValue} % \n')
                            self.rangoLuminosidad[f'L{i + 1}'] = True

                    else:
                        if self.rangoLuminosidad[f'L{i+1}']:
                            self.textoNotification.insert(tk.END,f'Sensor L{i+1} luminosidad normal: {ldrValue} % \n')
                            self.rangoLuminosidad[f'L{i+1}']=False

            self.updateTimeWindow()
            self.textoNotification.see(tk.END)

        except Exception as e:
            self.textoNotification.insert(tk.END,f'Error de conexión: {str(e)}\n')


    def updatePlots(self):
        try:
            x=list(range(len(self.timestamps)))
            for i,line in enumerate(self.tempLines):
                line.set_data(x,list(self.temperaturas[f'T{i+1}']))

            for i,line in enumerate(self.humeLines):
                line.set_data(x,list(self.humedades[f'H{i+1}']))

            for i,line in enumerate(self.ldrLines):
                line.set_data(x,list(self.luminosidad[f'L{i+1}']))

            for ax in (self.ax1, self.ax2, self.ax3):
                ax.relim()
                ax.autoscale_view()
            self.canvas.draw()

        except Exception as e:
            self.textoNotification.insert(tk.END,f'Error al graficar: {str(e)}\n')

    def sendcommand(self,event=None):
        if not self.connected:
            self.textoNotification.insert(tk.END,"Error, ESP32 sin Wi-Fi\n")
            return
        command=self.cmdEntry.get()
        if command:
            try:
                self.client_socket.sendall((command+"\n").encode())
                self.textoConsola.insert(tk.END,">>-"+command+"\n")
                self.cmdEntry.delete(0,tk.END)
            except Exception as e:
                self.textoNotification.insert(tk.END, "Error al enviar el comando {}\n".format(str(e)))

    def toggleAutoScroll(self):
        self.autoscroll=self.autoscrollvar.get()


    def establecerConexion(self):
        if not self.connected:
            self.connect()
        else:
            self.disconnect()

    def connect(self):
        ip = self.ipEntrada.get()
        port = int(self.puertoEntrada.get())
        try:
            self.client_socket=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            self.client_socket.connect((ip,port))
            self.connected = True
            self.buttomConnect.config(text="Desconectar")
            self.hiloDeRecepcion=threading.Thread(target=self.recibirDatos)
            self.hiloDeRecepcion.start()
            self.textoConsola.insert(tk.END,"Conectado a {}:{}\n".format(ip,port))


        except Exception as e:
            self.textoNotification.insert(tk.END, "Error de Conexión: {}\n".format(str(e)))
            print("Error de conexión:", str(e))

    def disconnect(self):
        if self.connected:
            self.client_socket.close()
        #self.textoConsola.insert(tk.END, "Error, no Conectado\n")
        #print("Error no conectado\n")
        self.buttomConnect.config(text="Conectar")
        self.textoConsola.insert(tk.END, "Desconectado\n")
        self.hiloDeRecepcion.join(timeout=0.5)
        self.connected=False


    def recibirDatos(self):
        buffer=b""
        while self.connected:
            try:
                data=self.client_socket.recv(1024)
                if not data:
                    break
                buffer += data
                while b"\n" in buffer:
                    linea,buffer = buffer.split(b"\n",1)
                    s=linea.decode().strip()
                    print(s)
                    self.procesarDatos(s)
                    self.textoConsola.insert(tk.END,"<<..."+s+"\n")
                    if self.autoscroll:
                        self.textoConsola.see(tk.END)

            except Exception as e:
                self.textoNotification.insert(tk.END, "Error recibir datos: {}\n".format(str(e)))
                break


if __name__ == "__main__":
    root = tk.Tk()
    app = esp32Interfaz(root)
    root.mainloop()