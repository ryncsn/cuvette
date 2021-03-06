import os
from pathlib import Path


DEFAULT_KS_APPEND = """
%post
# Fill your custom ks append here in cuvette
%end
"""


class Required:
    def __init__(self, v_type=None):
        self.v_type = v_type


class Settings(object):
    """
    Any setting defined here can be overridden by:

    Settings the appropriate environment variable, eg. to override FOOBAR, `export APP_FOOBAR="whatever"`.
    This is useful in production for secrets you do not wish to save in code and
    also plays nicely with docker(-compose). Settings will attempt to convert environment variables to match the
    type of the value here. See also activate.settings.sh.

    Or, passing the custom setting as a keyword argument when initialising settings (useful when testing)
    """
    _ENV_PREFIX = 'APP_'

    EXTRA_BEAKER_NS_MAP = {
    }

    BEAKER_JOB_DEFAULTS = {
        'job-group': 'libvirt-ci',
        'job-whiteboard': 'libvirt-ci-auto-cuvette',
        'job-packages': ['libselinux-python', 'gmp-devel', 'xz-devel'],
        'job-ksappend': DEFAULT_KS_APPEND
    }  # TODO: Shouldn't be here, will move it to a better place later

    BEAKER_URL = 'https://example.com'

    DB_NAME = Required(str)
    DB_USER = Required(str)
    DB_PASSWORD = Required(str)
    DB_HOST = 'localhost'
    DB_PORT = '27017'

    def __init__(self, **custom_settings):
        """
        :param custom_settings: Custom settings to override defaults, only attributes already defined can be set.
        """
        self._custom_settings = custom_settings
        self.substitute_environ()
        for name, value in custom_settings.items():
            if not hasattr(self, name):
                raise TypeError('{} is not a valid setting name'.format(name))
            setattr(self, name, value)

    def substitute_environ(self):
        """
        Substitute environment variables into settings.
        """
        for attr_name in dir(self):
            if attr_name.startswith('_') or attr_name.upper() != attr_name:
                continue

            orig_value = getattr(self, attr_name)
            is_required = isinstance(orig_value, Required)
            orig_type = orig_value.v_type if is_required else type(orig_value)
            env_var_name = self._ENV_PREFIX + attr_name
            env_var = os.getenv(env_var_name, None)
            if env_var is not None:
                if issubclass(orig_type, bool):
                    env_var = env_var.upper() in ('1', 'TRUE')
                elif issubclass(orig_type, int):
                    env_var = int(env_var)
                elif issubclass(orig_type, Path):
                    env_var = Path(env_var)
                elif issubclass(orig_type, bytes):
                    env_var = env_var.encode()
                # could do floats here and lists etc via json
                setattr(self, attr_name, env_var)
            elif is_required and attr_name not in self._custom_settings:
                raise RuntimeError('The required environment variable "{0}" is currently not set, '
                                   'you\'ll need to run `source activate.settings.sh` '
                                   'or you can set that single environment variable with '
                                   '`export {0}="<value>"`'.format(env_var_name))


try:
    from .settings_overlay import Settings as ExtraSettings
    for name in dir(ExtraSettings):
        if name.startswith('_'):
            continue
        setattr(Settings, name, getattr(ExtraSettings, name))
except ImportError:
    pass
