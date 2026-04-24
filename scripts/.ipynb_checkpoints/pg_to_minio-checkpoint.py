#!/usr/bin/env python3
"""
Batch loader from PostgreSQL to MinIO (S3)
СКРИПТ МОЖНО ЗАПУСКАТЬ СРАЗУ БЕЗ НАСТРОЕК
"""

from pyspark.sql import SparkSession

def create_spark_session():
    """Создание SparkSession + конфиг для MinIO"""
    spark = SparkSession.builder.appName("PostgresToMinIO").getOrCreate()

    hadoop_conf = spark._jsc.hadoopConfiguration()
    hadoop_conf.set("fs.s3a.access.key", "minio")
    hadoop_conf.set("fs.s3a.secret.key", "minio123")
    hadoop_conf.set("fs.s3a.endpoint", "http://minio:9000")
    hadoop_conf.set("fs.s3a.path.style.access", "true")

    return spark

def main():
    # JDBC параметры PostgreSQL
    jdbc_url = "jdbc:postgresql://postgres-src:5432/mydb"
    table = "orders"   # можно поменять
    user = "postgres"
    password = "postgres"

    # Выходной путь в MinIO
    output_path = "s3a://bucket/batch_output/"

    # Создаём SparkSession
    spark = create_spark_session()

    try:
        # Чтение из PostgreSQL
        df = spark.read \
            .format("jdbc") \
            .option("url", jdbc_url) \
            .option("dbtable", table) \
            .option("user", user) \
            .option("password", password) \
            .option("driver", "org.postgresql.Driver") \
            .load()

        print(f"загружено строк: {df.count()}")
        df.printSchema()

        # Запись в MinIO
        df.write.mode("overwrite").parquet(output_path)

    except Exception as e:
        print(str(e))
        raise e
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
