from .scheduler import setup as scheduler_setup
from .house_keeper import CleanExpiredMachine, CleanDeadMachine

__all__ = ['setup']


def setup(loop, app):
    # XXX: scheduler should run out side the app loop
    # XXX: Maybe after switch to celery after celery 4 is out
    scheduler = scheduler_setup(loop)
    for house_keeper in [CleanDeadMachine, CleanExpiredMachine]:
        house_keeper = house_keeper(app['db'])
        # Add tasks
        scheduler.add_job(house_keeper.run, 'interval', seconds=house_keeper.INTERVAL * 2)
