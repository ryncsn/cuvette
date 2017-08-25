from .pools import main_pool, provision_pool, transform_pool, reserved_pool, failure_pool
from .scheduler import setup as scheduler_setup, scheduler
from .house_keeper import house_keeping

__all__ = ['main_pool', 'provision_pool', 'transform_pool', 'reserved_pool',
           'failure_pool', 'setup']


def setup(loop):
    scheduler_setup(loop)
    scheduler.add_job(house_keeping, 'interval', seconds=10)