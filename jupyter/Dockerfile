FROM apache/spark:3.5.5-python3

USER root

# PySpark уже лежит в /opt/spark/python — просто пробрасываем в PYTHONPATH
ENV PYTHONPATH=/opt/spark/python:/opt/spark/python/lib/py4j-0.10.9.7-src.zip
ENV PYSPARK_PYTHON=python3

RUN pip install --no-cache-dir jupyterlab pandas matplotlib pyarrow

EXPOSE 8888 4040

CMD ["jupyter", "lab", "--ip=0.0.0.0", "--no-browser", "--allow-root", \
    "--ServerApp.token=", "--ServerApp.password="]