from pyflink.table import EnvironmentSettings, StreamTableEnvironment, Schema, DataTypes, TableDescriptor
from pyflink.datastream import StreamExecutionEnvironment


def main():
    s_env = StreamExecutionEnvironment.get_execution_environment()
    s_env.add_jars(
        "file:///opt/flink/lib/flink-sql-connector-kafka-3.3.0-1.20.jar")
    t_env = StreamTableEnvironment.create(s_env)
    t_env.get_config().set("parallelism.default", "1")

    t_env.create_temporary_table(
        "kafka_tickers",
        TableDescriptor.for_connector("kafka")
        .schema(Schema.new_builder()
                .column("symbol", DataTypes.STRING())
                .column("price", DataTypes.STRING())
                .column("volume_24h", DataTypes.STRING())
                .column("event_time", DataTypes.STRING())
                .build())
        .option("properties.bootstrap.servers", "kafka:9092")
        .option("topic", "crypto.tickers")
        .option("properties.group.id", "flink_fresh_group")
        .option("format", "json")
        .option("json.fail-on-missing-field", "false")
        .option("json.ignore-parse-errors", "true")
        .option("scan.startup.mode", "latest-offset")
        .build()
    )

    result = t_env.sql_query("""
        SELECT symbol,
               CAST(price AS DOUBLE)      AS price,
               CAST(volume_24h AS DOUBLE) AS volume_24h,
               event_time
        FROM kafka_tickers
        WHERE price IS NOT NULL AND price <> ''
    """)

    result.print_schema()
    t_env.to_changelog_stream(result).print()

    s_env.execute("crypto_tickers_test")


if __name__ == "__main__":
    main()
