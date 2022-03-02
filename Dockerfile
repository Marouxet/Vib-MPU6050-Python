# syntax=docker/dockerfile:1

FROM python:3.9

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install pyproject-toml
RUN pip install --upgrade pip
RUN pip install kivy --no-binary=all
RUN pip numpy==1.19
RUN pip install PySerial
RUN pip install kivy_garden.graph
RUN pip install matplotlib
RUN pip install scipy


COPY . .

# Creo una variable de entorno para ser usada luego en el script
#ENV ARDUINO_UNTREF test

CMD [ "python3", "mpu6050Arduino.py"]