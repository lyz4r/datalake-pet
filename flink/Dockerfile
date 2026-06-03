FROM apache/flink:1.20-scala_2.12
RUN apt-get update && apt-get install -y python3-pip
RUN ln -s /usr/bin/python3 /usr/bin/python
RUN pip install apache-flink==1.20.0
ADD https://repo1.maven.org/maven2/org/apache/flink/flink-sql-connector-kafka/3.3.0-1.20/flink-sql-connector-kafka-3.3.0-1.20.jar \
    /opt/flink/lib/
ADD https://repo1.maven.org/maven2/org/apache/flink/flink-metrics-prometheus/1.20.0/flink-metrics-prometheus-1.20.0.jar \
    /opt/flink/lib/
RUN cp /opt/flink/opt/flink-s3-fs-hadoop-*.jar /opt/flink/lib/ \
 && chmod 644 /opt/flink/lib/*.jar