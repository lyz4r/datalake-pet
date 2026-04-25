@echo off
setlocal

set DEST=spark\jars
set BASE=https://repo1.maven.org/maven2
if not exist %DEST% mkdir %DEST%

set JARS=^
com/clickhouse/clickhouse-jdbc/0.5.0/clickhouse-jdbc-0.5.0-all.jar ^
com/amazonaws/aws-java-sdk-bundle/1.12.526/aws-java-sdk-bundle-1.12.526.jar ^
org/apache/commons/commons-pool2/2.12.0/commons-pool2-2.12.0.jar ^
org/apache/hadoop/hadoop-auth/3.3.6/hadoop-auth-3.3.6.jar ^
org/apache/hadoop/hadoop-aws/3.3.6/hadoop-aws-3.3.6.jar ^
org/apache/hadoop/hadoop-common/3.3.6/hadoop-common-3.3.6.jar ^
org/apache/iceberg/iceberg-spark-runtime-3.5_2.12/1.5.2/iceberg-spark-runtime-3.5_2.12-1.5.2.jar ^
org/apache/kafka/kafka-clients/3.4.1/kafka-clients-3.4.1.jar ^
org/postgresql/postgresql/42.6.0/postgresql-42.6.0.jar ^
org/apache/spark/spark-sql-kafka-0-10_2.12/3.5.0/spark-sql-kafka-0-10_2.12-3.5.0.jar ^
org/apache/spark/spark-token-provider-kafka-0-10_2.12/3.5.0/spark-token-provider-kafka-0-10_2.12-3.5.0.jar

for %%J in (%JARS%) do (
    for %%F in (%%J) do (
        if exist "%DEST%\%%~nxF" (
            echo [skip] %%~nxF
        ) else (
            echo [get ] %%~nxF
            curl -fL --retry 3 -o "%DEST%\%%~nxF" "%BASE%/%%J" || echo FAILED: %%J
        )
    )
)

echo Done.
endlocal