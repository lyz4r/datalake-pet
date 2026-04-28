FROM apache/spark:3.5.5-python3

USER root

# JAR versions chosen for Spark 3.5.5 compatibility
ENV HADOOP_AWS_VERSION=3.3.4 \
  AWS_SDK_VERSION=1.12.262 \
  SPARK_KAFKA_VERSION=3.5.5 \
  KAFKA_CLIENTS_VERSION=3.5.1 \
  COMMONS_POOL_VERSION=2.11.1 \
  CLICKHOUSE_JDBC_VERSION=0.6.5 \
  ICEBERG_VERSION=1.10.1

RUN set -eux; \
  cd /opt/spark/jars; \
  for url in \
  https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/${HADOOP_AWS_VERSION}/hadoop-aws-${HADOOP_AWS_VERSION}.jar \
  https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/${AWS_SDK_VERSION}/aws-java-sdk-bundle-${AWS_SDK_VERSION}.jar \
  https://repo1.maven.org/maven2/org/apache/spark/spark-sql-kafka-0-10_2.12/${SPARK_KAFKA_VERSION}/spark-sql-kafka-0-10_2.12-${SPARK_KAFKA_VERSION}.jar \
  https://repo1.maven.org/maven2/org/apache/spark/spark-token-provider-kafka-0-10_2.12/${SPARK_KAFKA_VERSION}/spark-token-provider-kafka-0-10_2.12-${SPARK_KAFKA_VERSION}.jar \
  https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/${KAFKA_CLIENTS_VERSION}/kafka-clients-${KAFKA_CLIENTS_VERSION}.jar \
  https://repo1.maven.org/maven2/org/apache/commons/commons-pool2/${COMMONS_POOL_VERSION}/commons-pool2-${COMMONS_POOL_VERSION}.jar \
  https://repo1.maven.org/maven2/com/clickhouse/clickhouse-jdbc/${CLICKHOUSE_JDBC_VERSION}/clickhouse-jdbc-${CLICKHOUSE_JDBC_VERSION}-all.jar \
  https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-spark-runtime-3.5_2.12/${ICEBERG_VERSION}/iceberg-spark-runtime-3.5_2.12-${ICEBERG_VERSION}.jar \
  https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-aws-bundle/${ICEBERG_VERSION}/iceberg-aws-bundle-${ICEBERG_VERSION}.jar \
  ; do \
  curl -fL -o "$(basename $url)" "$url"; \
  done

# Default Spark config (S3/MinIO + Iceberg extension)
COPY spark-defaults.conf /opt/spark/conf/spark-defaults.conf

RUN pip install --no-cache-dir clickhouse-connect==0.8.*

USER spark