# api/src/worker.py

import asyncio
import logging
from .utils.jobs.broker import job_broker
from .services.job_service import job_manager
from .db.session import AsyncSessionLocal
from .utils.seeding_engine import SeedingEngine
from .utils.ml.registry import ModelRegistry
import pandas as pd
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("burstdb_worker")

async def process_jobs():
    logger.info("Worker started, listening for jobs...")
    
    while True:
        job_data = await job_broker.get_next_job("worker_group", "worker_1")
        if not job_data:
            await asyncio.sleep(1)
            continue
            
        msg_id, data = job_data
        job_id = uuid.UUID(data["job_id"])
        job_type = data["job_type"]
        params = data["parameters"]
        
        async with AsyncSessionLocal() as db:
            logger.info(f"Processing job {job_id} ({job_type})")
            await job_manager.update_job_status(db, job_id, "running", progress=0.1)
            
            try:
                if job_type == "synthetic_generation":
                    # 1. Seeding
                    seeding = SeedingEngine()
                    # Mocking schema for now, in real it would be from DB
                    seed_rows = seeding.generate_seed_rows("test_table", [{"name": "id", "type": "int"}], 100)
                    await job_manager.update_job_status(db, job_id, "running", progress=0.4)
                    
                    # 2. Generation
                    df_seed = pd.DataFrame(seed_rows)
                    algo = params.get("algorithm", "ctgan")
                    plugin = ModelRegistry.get_plugin(algo)
                    plugin.fit(df_seed, params)
                    await job_manager.update_job_status(db, job_id, "running", progress=0.7)
                    
                    synthetic_df = plugin.generate(params.get("n_rows", 1000))
                    
                    # 3. Store results (Arrow)
                    # Implementation for storage upload goes here
                    
                    await job_manager.update_job_status(db, job_id, "completed", progress=1.0)
                
                await job_broker.ack_job("worker_group", msg_id)
                logger.info(f"Job {job_id} completed successfully")
                
            except Exception as e:
                logger.error(f"Job {job_id} failed: {e}")
                await job_manager.update_job_status(db, job_id, "failed", error=str(e))

if __name__ == "__main__":
    asyncio.run(process_jobs())
