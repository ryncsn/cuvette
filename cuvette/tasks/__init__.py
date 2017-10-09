"""
Provisoiners
"""
import logging

from cuvette.tasks.base import BaseTask, Tasks
from .provision import ProvisionTask
from .inspect import InspectTask
from .reserve import ReserveTask
from .teardown import TeardownTask

logger = logging.getLogger(__name__)

__all__ = ['BaseTask', 'ProvisionTask', 'InspectTask', 'ReserveTask', 'TeardownTask', 'Tasks']
