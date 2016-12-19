import os
import sys
import time
import atexit
import base64
import multiprocessing.managers

__all__ = ['Stance', 'StanceException']


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


class StanceException(Exception):
    """ Base Exception class for errors that occur in this module. """


class Stance:
    """ Self-instantiating worker process. Will intelligently run a single instance
        of a registered class, by either creating that instance or connecting to it.
        Utilizes the :mod:`multiprocessing.managers` interface for secure local-machine
        processes and management.

        Args:
            _class (class): Class that gets instantiated one time, and can be accessed
                across other process instances.
            port (int): Port that determines where an instance is created, used as a lock
                for preventing more than one to be running at a given time.
            secret (str): Connection secret used for TLS communication. If ``secret``
                is left as ``None`` the default (``secret``) is used.
    """

    __slots__ = (
        '_class', '_port', '_secret', '_instance', '_new_instance'
    )

    def __init__(self, _class, *, port, secret=None):
        if secret is None:
            secret = 'secret'

        self._class = _class
        self._port = int(port)
        self._secret = base64.b64encode(b'%d_%s' % (self._port, secret.encode('utf-8')))
        self._instance = None
        self._new_instance = False

    def __repr__(self):
        return '<Stance cls="%s" port=%d secret=%s is_new=%s>' % (
            self._class.__name__, self.port, self._secret[0:8].decode('utf-8'), self.is_new)

    @classmethod
    def create(cls, _class, *, port, secret=None, args=None, kwargs=None):
        """ Performs a :obj:`.Stance` init and register for a given _class.

            Args:
                _class (class)
                port (int)
                secret (str)
                args (tuple): arguments passed into ``_class.__init__``.
                kwargs (dict): keyword arguments passed into ``_class.__init__``.

            Returns:
                :obj:`.Stance`
        """
        args = tuple(args) if args else tuple()
        kwargs = dict(kwargs) if kwargs else dict()

        o = cls(_class, port=port, secret=secret)
        o.register(*args, **kwargs)
        return o

    @property
    def inst(self):
        """ Returns the instance of the underlying :obj:`._class` object. """
        return self._instance

    @property
    def is_new(self):
        """ Swallows :obj:`.StanceException` checking for instance newness. """
        try:
            return self.created_new_instance()
        except StanceException:
            return None

    @property
    def port(self):
        """ Returns the port number of the registered class / instance. """
        return self._port

    def created_new_instance(self):
        """ Checks if the instance was created or connected to.

            Raises:
                StanceException: when :func:`.register` hasn't been called yet.

            Returns:
                bool
        """
        if not self._instance:
            raise StanceException('instance has not yet been registered')
        return self._new_instance

    def register(self, *args, **kwargs):
        """ Creates or connects to an instance of :attr:`._class` depending
            on whether it already exists or not. Arguments are passed to the
            underlying ``__init__`` function when the instance is created.

            Args:
                args (tuple)
                kwargs (dict)

            Raises:
                StanceException: when :obj:`.Stance` is unable to create or
                    connect to an existing instance of :attr:`._class`.

            Returns:
                Instance of ``._class``.
        """
        class ClassManager(multiprocessing.managers.BaseManager):
            pass

        if self._instance:
            return self._instance

        try:
            # first try to connect to an existing instance
            with open(os.devnull, 'w') as devnull:
                with _SuppressStdErr(devnull=devnull):
                    self._connect(ClassManager)

        except (ConnectionAbortedError, ConnectionRefusedError):
            # second, if you can't connect to an existing instance
            # create a new networked-instance via ClassManager
            try:
                with open(os.devnull, 'w') as devnull:
                    with _SuppressStdErr(devnull=devnull):
                        self._start(ClassManager, args, kwargs)

            except Exception:
                # lastly, re-attempt to connect to networked-instance
                time.sleep(1)
                self._connect(ClassManager)

        except Exception as e:
            # unexpected failure, raise it
            raise StanceException(e)

        return self._instance

    def _connect(self, class_manager):
        """ Private method to connect to external process. """
        class_manager.register('get_instance')
        manager = class_manager(address=('', self._port), authkey=self._secret)
        manager.connect()
        self._instance = manager.get_instance()

    def _start(self, class_manager, args, kwargs):
        """ Private method to start an external process. """
        instance = self._class(*args, **kwargs)
        class_manager.register('get_instance', callable=lambda: instance)
        manager = class_manager(address=('', self._port), authkey=self._secret)
        manager.start()
        atexit.register(manager.shutdown)
        self._instance = manager.get_instance()
        self._new_instance = True
