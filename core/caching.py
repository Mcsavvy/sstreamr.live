from django.core.cache import caches

memcache = caches['memcache']
filecache = caches['filecache']
dbcache = caches['dbcache']
default = caches['default']


class CachedObject:
    DEFAULT = {
        'cache': dbcache
    }

    def __init__(self, key, **settings):
        self.settings = dict(
            cache=self.DEFAULT['cache'],
            version=None,
            timeout=60,
        ) | settings
        self._key = key

    def set(
        self,
        value,
        version=None,
        timeout=None
    ):
        version = version or self.settings['version']
        timeout = version or self.settings['timeout']
        self.settings['cache'].set(
            self._key, value, timeout=timeout, version=version
        )

    def get(
        self,
        default=None,
        version=None,
        timeout=None
    ):
        version = version or self.settings['version']
        timeout = version or self.settings['timeout']
        _get = self.settings['cache'].get(self._key, version=version)
        if not _get and default:
            self.set(default, version=version, timeout=timeout)
            return self.settings['cache'].get(self._key, default, version)
        return _get
