import asyncio

from datetime import datetime

from cuvette.pipeline.task import TeardownTask
from cuvette.pool.machine import Machine


HOUSE_KEEPING_FREQ = 5


async def house_keeping():
    """
    The worker function that keep scanning
    main pool to clean expired machines
    """
    teardown_tasks = []
    for machine in await Machine.find_all({
        'expire_time': {
            '$lte': datetime.now()
        }
    }):
        if any(task['type'] == 'teardown' for task in machine['tasks'].values()):
            continue  # TODO: use mongo query
        teardown_tasks.append(TeardownTask([machine]).run())
    # Wait for 30s for tasks to finished, else change into async mode
    if teardown_tasks:
        finished, pending = await asyncio.wait(teardown_tasks, timeout=HOUSE_KEEPING_FREQ)
