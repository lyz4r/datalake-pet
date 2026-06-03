import json
import logging
from dataclasses import dataclass

from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.connectors.kafka import (
    KafkaSource, KafkaSink, KafkaOffsetsInitializer,
    KafkaRecordSerializationSchema,
)
from pyflink.common.serialization import SimpleStringSchema
from pyflink.common import WatermarkStrategy
from pyflink.datastream.functions import KeyedProcessFunction, RuntimeContext, FlatMapFunction
from pyflink.datastream.state import ValueStateDescriptor
from pyflink.common.typeinfo import Types

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

PRICE_DELTA_THRESHOLD = 0.001


@dataclass
class CoinPrice:
    coin_id: str
    symbol: str
    name: str
    price_usd: float
    market_cap: float
    volume_24h: float
    high_24h: float
    low_24h: float
    last_updated: str


class ParsePrices(FlatMapFunction):
    def flat_map(self, raw: str):
        try:
            coins = json.loads(raw)
            if not isinstance(coins, list):
                return
            for c in coins:
                price = c.get("current_price")
                if price is None:
                    continue
                yield CoinPrice(
                    coin_id=c.get("id", ""),
                    symbol=(c.get("symbol") or "").upper(),
                    name=c.get("name", ""),
                    price_usd=float(price),
                    market_cap=float(c.get("market_cap") or 0),
                    volume_24h=float(c.get("total_volume") or 0),
                    high_24h=float(c.get("high_24h") or 0),
                    low_24h=float(c.get("low_24h") or 0),
                    last_updated=c.get("last_updated", ""),
                )
        except Exception as e:
            log.warning(f"Failed to parse message: {e}")


class PriceAlertFunction(KeyedProcessFunction):
    def open(self, ctx: RuntimeContext):
        self.prev_price_state = ctx.get_state(
            ValueStateDescriptor("prev_price", Types.FLOAT())
        )

    def process_element(self, coin: CoinPrice, ctx: KeyedProcessFunction.Context):
        prev_price = self.prev_price_state.value()

        if prev_price is None:
            self.prev_price_state.update(coin.price_usd)
            return

        delta_pct = (coin.price_usd - prev_price) / prev_price
        self.prev_price_state.update(coin.price_usd)

        if abs(delta_pct) >= PRICE_DELTA_THRESHOLD:
            direction = "▲" if delta_pct > 0 else "▼"
            alert = {
                "coin_id":    coin.coin_id,
                "symbol":     coin.symbol,
                "prev_price": round(prev_price, 4),
                "curr_price": round(coin.price_usd, 4),
                "delta_pct":  round(delta_pct * 100, 2),
                "direction":  direction,
                "last_updated": coin.last_updated,
            }
            log.warning(
                f"ALERT {direction} {coin.symbol}: {alert['delta_pct']}%")
            yield json.dumps(alert)


def main():
    env = StreamExecutionEnvironment.get_execution_environment()
    env.set_parallelism(4)

    source = (
        KafkaSource.builder()
        .set_bootstrap_servers("kafka:9092")
        .set_topics("crypto.prices")
        .set_group_id("flink_prices_alerting")
        .set_starting_offsets(KafkaOffsetsInitializer.latest())
        .set_value_only_deserializer(SimpleStringSchema())
        .build()
    )

    sink = (
        KafkaSink.builder()
        .set_bootstrap_servers("kafka:9092")
        .set_record_serializer(
            KafkaRecordSerializationSchema.builder()
            .set_topic("crypto.alerts")
            .set_value_serialization_schema(SimpleStringSchema())
            .build()
        )
        .build()
    )

    (
        env

        .from_source(source, WatermarkStrategy.no_watermarks(), "prices_source")
        .set_parallelism(3)

        .flat_map(ParsePrices(), output_type=Types.PICKLED_BYTE_ARRAY())
        .key_by(lambda c: c.coin_id)
        .process(PriceAlertFunction(), output_type=Types.STRING())
        .sink_to(sink)
    )

    env.execute("crypto_price_alerts")


if __name__ == "__main__":
    main()
