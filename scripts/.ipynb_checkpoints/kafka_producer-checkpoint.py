import json
import time
import random
from datetime import datetime
from kafka import KafkaProducer

"""
Kafka Producer для отправки структурированных данных в топик Kafka.

Конфигурация:
- KAFKA_BROKER: Адрес и порт брокера Kafka (по умолчанию localhost:29092)
- TOPIC_NAME: Название топика для отправки данных (по умолчанию sensor_metrics)
"""

# Конфигурация Kafka
KAFKA_BROKER = 'localhost:29092'  # Брокер Kafka в формате host:port (внешний доступ)
TOPIC_NAME = 'sensor_metrics'    # Топик для отправки данных

# Инициализация producer с JSON сериализацией
producer = KafkaProducer(
    bootstrap_servers=[KAFKA_BROKER],  # Подключение к указанному брокеру Kafka
    value_serializer=lambda v: json.dumps(v).encode('utf-8')  # Сериализация данных в JSON
)

def generate_sensor_data():
    """
    Генерация структурированных данных в формате JSON.
    
    Возвращает:
        dict: Словарь с полями:
            - id: Уникальный идентификатор сообщения
            - timestamp: Временная метка в ISO формате
            - value: Словарь с показаниями датчиков
    """
    return {
        'id': str(random.getrandbits(64)),  # Генерация уникального 64-битного ID
        'timestamp': datetime.now().isoformat(),
        'value': {
            'sensor_id': f"sensor_{random.randint(1, 100)}",  # Случайный ID сенсора от 1 до 100
            'temperature': round(random.uniform(18.0, 32.0), 2),  # Температура от 18.0 до 32.0 с округлением до 2 знаков
            'humidity': random.randint(30, 90),  # Влажность от 30% до 90%
            'pressure': random.randint(950, 1050)  # Давление от 950 до 1050 hPa
        }
    }

def main():
    """
    Основная функция producer:
    - Подключается к Kafka
    - Генерирует и отправляет данные в бесконечном цикле
    - Обрабатывает прерывание (Ctrl+C)
    """
    print(f"Starting Kafka producer. Broker: {KAFKA_BROKER}, Topic: {TOPIC_NAME}")
    try:
        while True:
            # Генерация и отправка данных
            data = generate_sensor_data()
            producer.send(TOPIC_NAME, value=data)  # Отправка данных в указанный топик Kafka
            print(f"Sent message ID: {data['id']}")
            
            # Интервал между сообщениями (2 секунды)
            time.sleep(2)  # Пауза 2 секунды между сообщениями
    except KeyboardInterrupt:
        print("\nStopping producer...")
    finally:
        producer.close()
        print("Producer stopped.")

if __name__ == "__main__":
    main()