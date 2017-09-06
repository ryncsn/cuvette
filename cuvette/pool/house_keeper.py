import asyncio

from datetime import datetime

from cuvette.pipeline.task import TeardownTask
from cuvette.pool import main_pool


HOUSE_KEEPING_FREQ = 15


async def house_keeping():
    """
    The worker function that keep scanning
    main pool to clean expired machines
    """
    teardown_tasks = []
    async for machine in main_pool.find({
        'expire_time': {
            '$lte': datetime.now()
        }
    }):
        if any(task['type'] == 'teardown' for task in machine['tasks']):
            continue  # TODO: use mongo query
        teardown_tasks.append(TeardownTask([machine]).run())
    # Wait for 30s for tasks to finished, else change into async mode
    if teardown_tasks:
        finished, pending = await asyncio.wait(teardown_tasks, timeout=HOUSE_KEEPING_FREQ)
