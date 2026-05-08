FROM apache/airflow:3.2.1-python3.12

USER root
RUN apt-get update && apt-get install -y --no-install-recommends --fix-missing \
        curl \
        openjdk-17-jre-headless \
    && rm -rf /var/lib/apt/lists/*

ARG SPARK_VERSION=3.5.5
RUN curl -fsSL https://archive.apache.org/dist/spark/spark-${SPARK_VERSION}/spark-${SPARK_VERSION}-bin-hadoop3.tgz \
    | tar -xz -C /opt \
    && ln -s /opt/spark-${SPARK_VERSION}-bin-hadoop3 /opt/spark

ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV SPARK_HOME=/opt/spark
ENV PATH=$SPARK_HOME/bin:$PATH

USER airflow
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-3.2.1/constraints-3.12.txt" \
    -r /requirements.txt
