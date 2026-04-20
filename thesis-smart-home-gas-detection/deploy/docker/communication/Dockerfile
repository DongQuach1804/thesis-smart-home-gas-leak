FROM python:3.11.9-slim

WORKDIR /app

COPY communication/bridges/requirements-bridge.txt /tmp/requirements-bridge.txt
RUN pip install --no-cache-dir -r /tmp/requirements-bridge.txt

COPY communication /app/communication

CMD ["python", "communication/bridges/mqtt_kafka_bridge.py"]
