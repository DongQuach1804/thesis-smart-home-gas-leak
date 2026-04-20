FROM python:3.11.9-slim

WORKDIR /app

COPY device/simulator/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY device /app/device

CMD ["python", "device/simulator/sensor_simulator.py"]
