import os
import sys
import time
import atexit
import multiprocessing.managers


class _SuppressStdErr(object):
    def __init__(self, devnull):
        self._devnull = devnull

    def __enter__(self):
        sys.stderr.flush()
        self._stderr = sys.stderr
        sys.stderr = self._devnull

    def __exit__(self, exc_type, exc_value, traceback):
        sys.stderr.flush()
        sys.stderr = self._stderr


class Stance:
    def __init__(self, clazz, port, secret='secret'):
        self._clazz = clazz
        self._port = port
        self._secret = secret.encode('utf-8')
        self._instance = None
        self._new_instance = False

    def created_new_instance(self):
        if not self._instance:
            raise Exception('instance has not yet been registered')
        return self._new_instance

    def register(self, *args, **kwargs):
        if self._instance:
            return self._instance

        class ClazzManager(multiprocessing.managers.BaseManager):
            pass

        try:
            with open(os.devnull, 'w') as devnull:
                with _SuppressStdErr(devnull=devnull):
                    self._connect(ClazzManager)
        except:
            try:
                with open(os.devnull, 'w') as devnull:
                    with _SuppressStdErr(devnull=devnull):
                        self._start(ClazzManager, args, kwargs)
            except:
                time.sleep(1)
                self._connect(ClazzManager)

        return self._instance

    def _connect(self, clazz_manager):
        clazz_manager.register('get_instance')
        manager = clazz_manager(address=('', self._port), authkey=self._secret)
        manager.connect()
        self._instance = manager.get_instance()

    def _start(self, clazz_manager, args, kwargs):
        instance = self._clazz(*args, **kwargs)
        clazz_manager.register('get_instance', callable=lambda: instance)
        manager = clazz_manager(address=('', self._port), authkey=self._secret)
        manager.start()
        atexit.register(manager.shutdown)
        self._instance = manager.get_instance()
        self._new_instance = True
