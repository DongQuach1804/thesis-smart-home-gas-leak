FROM python:3.11.9-slim

WORKDIR /app
ARG PIP_INDEX_URL=https://pypi.org/simple

# ── System deps: Java (required by PySpark) ───────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    openjdk-17-jre-headless \
    curl \
    procps \
    && rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PYSPARK_PYTHON=python3

# ── Python dependencies ───────────────────────────────────────────────────────
# Copy requirements first for Docker layer caching
COPY processing/requirements-processing.txt /tmp/requirements-processing.txt

# Upgrade pip first to fix hash-validation bugs in pip 24.0
RUN python -m pip install --upgrade pip setuptools wheel

# Install torch CPU-only BEFORE main requirements (avoids 4GB CUDA download
# that stable-baselines3 would otherwise trigger)
RUN python -m pip install --no-cache-dir \
    torch==2.6.0 --index-url https://download.pytorch.org/whl/cpu

# Use isolated mode + explicit index to avoid hash mismatches from external pip config/mirrors.
RUN python -m pip --isolated install --no-cache-dir \
   --index-url ${PIP_INDEX_URL} \
   --trusted-host pypi.org \
   --trusted-host files.pythonhosted.org \
   --timeout=120 \
   --retries=10 \
   --prefer-binary \
   -r /tmp/requirements-processing.txt

# ── Download Spark-Kafka connector JARs ───────────────────────────────────────
# These are needed for pyspark readStream.format("kafka") to work.
# Spark 3.5.x → kafka connector 3.5.1, Scala 2.12
RUN PYSPARK_JARS=$(python3 -c "import pyspark, os; print(os.path.join(os.path.dirname(pyspark.__file__), 'jars'))") \
    && echo "Downloading Spark-Kafka JARs to ${PYSPARK_JARS}" \
    && curl -fsSL --retry 3 \
       "https://repo1.maven.org/maven2/org/apache/spark/spark-sql-kafka-0-10_2.12/3.5.1/spark-sql-kafka-0-10_2.12-3.5.1.jar" \
       -o "${PYSPARK_JARS}/spark-sql-kafka-0-10_2.12-3.5.1.jar" \
    && curl -fsSL --retry 3 \
       "https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/3.4.1/kafka-clients-3.4.1.jar" \
       -o "${PYSPARK_JARS}/kafka-clients-3.4.1.jar" \
    && curl -fsSL --retry 3 \
       "https://repo1.maven.org/maven2/org/apache/spark/spark-token-provider-kafka-0-10_2.12/3.5.1/spark-token-provider-kafka-0-10_2.12-3.5.1.jar" \
       -o "${PYSPARK_JARS}/spark-token-provider-kafka-0-10_2.12-3.5.1.jar" \
    && curl -fsSL --retry 3 \
       "https://repo1.maven.org/maven2/org/apache/commons/commons-pool2/2.11.1/commons-pool2-2.11.1.jar" \
       -o "${PYSPARK_JARS}/commons-pool2-2.11.1.jar" \
    && echo "JAR downloads complete"

# ── Copy processing source ────────────────────────────────────────────────────
COPY processing /app

# ── Run the stream processor (embedded local Spark — no external cluster) ─────
CMD ["python", "spark-streaming/jobs/stream_processor.py"]
