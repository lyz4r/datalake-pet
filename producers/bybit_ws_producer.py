import asyncio
import orjson
import logging
import websockets


from utils.kafka_client import KafkaClient

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

WS_URL = "wss://stream.bybit.com/v5/public/spot"
SUBSCRIBE_MSG = {
    "op": "subscribe",
    "args": ["tickers.BTCUSDT"]
}
KAFKA_TOPIC = "crypto.tickers"


async def connect_to_bybit(uri: str, subscribe_msg: dict):
    log.info("Connecting to %s", uri)
    with KafkaClient() as producer:
        try:
            async with websockets.connect(uri) as ws:
                log.info("Connected")
                await ws.send(orjson.dumps(subscribe_msg))
                log.info("Sent subscription: %s", subscribe_msg)
                async for raw in ws:
                    msg = orjson.loads(raw)
                    data = msg.get("data")
                    if not isinstance(data, dict):
                        continue
                    flat = {
                        "symbol":     data.get("symbol"),
                        "price":      data.get("lastPrice"),
                        "volume_24h": data.get("volume24h"),
                        "event_time": str(msg.get("ts", "")),
                    }
                    producer.send(KAFKA_TOPIC, value=flat)
        except websockets.exceptions.InvalidStatus as e:
            log.error(f"Крымчанам соболезную: {e}")
        except Exception as e:
            log.error(
                f"Could not connect to Bybit WebSocket: {e}, reconnecting in 5s")
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(connect_to_bybit(WS_URL, SUBSCRIBE_MSG))
