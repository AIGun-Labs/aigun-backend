from data.rabbit import RabbitConfig, RabbitMQ
from pydantic import BaseModel
from typing import Union
import os


config = RabbitConfig(os.getenv('RABBIT_URL', 'amqp://user:password@localhost:5672/'),)


class TestDataModel(BaseModel):
    id: int
    name: str


async def producer():
    rabbit = RabbitMQ(config)
    await rabbit.ensure_connection()

    await rabbit.send('test_queue', TestDataModel(id=1, name='test'))
    await rabbit.close()


async def consumer():
    rabbit = RabbitMQ(config)
    async for data, msg in rabbit.receive('test_queue', TestDataModel):
        try:
            print(data.model_dump_json(indent=2))
            await msg.ack()
        except Exception as e:
            await msg.reject(requeue=True)
            print(e)
    async for data, msg in rabbit.receive('test_queue', dict | list):
        try:
            print(data)
            await msg.ack()
        except Exception as e:
            await msg.reject(requeue=True)
            print(e)
