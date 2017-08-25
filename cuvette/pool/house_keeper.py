import cuvette.provisioners as provisioner

from datetime import datetime
from .pools import main_pool


async def house_keeping():
    """
    The worker function that keep scanning
    main pool to clean expired machines
    """
    async for machine in main_pool.find({
        'expire_time': {
            '$lte': datetime.now()
        }
    }):
        provisioner_name = machine['provisioner']
        provisioner.Provisioners[provisioner_name].teardown(machine)
