from pyspark.sql import SparkSession

# --- 1. Spark session ---
spark = SparkSession.builder.appName("KafkaToMinIO").getOrCreate()

# --- 2. Настройка доступа к MinIO ---
hadoop_conf = spark._jsc.hadoopConfiguration()
hadoop_conf.set("fs.s3a.access.key", "minio")
hadoop_conf.set("fs.s3a.secret.key", "minio123")
hadoop_conf.set("fs.s3a.endpoint", "http://minio:9000")
hadoop_conf.set("fs.s3a.path.style.access", "true")

# --- 3. Чтение из Kafka ---
df = spark.readStream.format("kafka")\
    .option("kafka.bootstrap.servers", "kafka:9092")\
    .option("subscribe", "pg.public.orders")\
    .option("startingOffsets", "earliest")\
    .load()

df_str = df.selectExpr("CAST(value AS STRING)")

# --- 4. Запись в MinIO ---
query_minio = df_str.writeStream \
    .format("parquet") \
    .option("checkpointLocation", "/tmp/checkpoint") \
    .option("path", "s3a://bucket/kafka_output") \
    .start()

query_minio.awaitTermination()