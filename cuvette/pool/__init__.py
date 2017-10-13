from .pools import get_main_pool, get_failure_pool
from .pools import setup as pool_db_setup
from .scheduler import setup as scheduler_setup
from .house_keeper import Worker as HouseKeeper

__all__ = ['get_main_pool', 'get_failure_pool', 'setup']


def setup(loop, app):
    app['db'] = pool_db_setup(app['settings'])

    # XXX: scheduler should run out side the app loop
    # XXX: Maybe after switch to celery after celery 4 is out
    scheduler = scheduler_setup(loop)
    house_keeper = HouseKeeper(app['db'])

    # Add tasks
    scheduler.add_job(house_keeper.run, 'interval', seconds=HouseKeeper.HOUSE_KEEPING_INTERVAL * 2)
