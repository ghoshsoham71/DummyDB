# api/src/utils/jobs/broker.py

import os
import json
import redis.asyncio as redis
from redis.exceptions import ResponseError
from typing import Dict, Any, Optional

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

class JobBroker:
    def __init__(self):
        self.redis = redis.from_url(REDIS_URL, decode_responses=True)
        self.stream_name = "burstdb_jobs"

    async def enqueue_job(self, job_id: str, job_type: str, parameters: Dict[str, Any]):
        payload = {
            "job_id": job_id,
            "job_type": job_type,
            "parameters": json.dumps(parameters)
        }
        await self.redis.xadd(self.stream_name, payload)

    async def get_next_job(self, group_name: str, consumer_name: str):
        # Create group if not exists
        try:
            await self.redis.xgroup_create(self.stream_name, group_name, id="0", mkstream=True)
        except ResponseError:
            pass # Group already exists

        messages = await self.redis.xreadgroup(group_name, consumer_name, {self.stream_name: ">"}, count=1)
        if not messages:
            return None
        
        msg_id, data = messages[0][1][0]
        data["parameters"] = json.loads(data["parameters"])
        return msg_id, data

    async def ack_job(self, group_name: str, msg_id: str):
        await self.redis.xack(self.stream_name, group_name, msg_id)

job_broker = JobBroker()
