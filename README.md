# stance

**stance** provides self-instantiating worker processes for Python 3. It is best used with
[WSGI](https://www.python.org/dev/peps/pep-0333/) applications, like a [flask](http://flask.pocoo.org/) web server,
where the forking of processes takes place, before the user gains control.

In order to provide this functionality, stance does not need any external dependencies and no worker processes
controlled by the operating system (e.g. with [systemd](https://www.freedesktop.org/wiki/Software/systemd/)). To some
extent, stance is a light-weight alternative to [Celery](http://www.celeryproject.org/) with
[RabbitMQ](http://www.rabbitmq.com/) or other external message brokers.

## Quick start

```bash
pip3 install --user stance
```

First create a stance object and define the class to be instantiated with it, as well as a free system port.
The connection to the system port is TLS encrypted and it is recommended to define a custom secret. In order to create
an instance of the class, call the `register` method with the necessary constructor arguments.

**examples/counter.py**

```python
from time import sleep
from stance import Stance


class Counter:
    def __init__(self, start_value=0):
        self._count = start_value

    def increment(self):
        self._count += 1

    def get_count(self):
        return self._count

s = Stance(clazz=Counter, port=17310, secret='PASSWORD')
counter = s.register(start_value=100)

if s.created_new_instance():
    print('enter infinite loop...')
    while True:    
        sleep(1)

counter.increment()
print(counter.get_count())
```

If the script is run for the first time, a new instance of Counter will be registered. The `created_new_instance` method
will return `true` and the script goes into an infinite loop. The counter will be served on the specified port, as long as
the script is running. If another Python interpreter runs the exact same script, the `register` method will return the
existing counter, instead of creating a new one. It will not end in the infinite loop, but instead increments the
counter and prints the result.

```bash
# start the first interpreter as a background job
python3 examples/counter.py &

for i in $(seq 1 10); do
    # increment the counter by running the script multiple times
    python3 examples/counter.py
done

# terminate the background job
kill %%
```

## Usage with Apache2, mod_wsgi and flask

Install Apache2, mod_wsgi for Python3 and flask:

```bash
sudo apt install apache2 libapache2-mod-wsgi-py3
pip3 install --user flask
```

A web application can profit from **multiprocessing** to speed up requests and to fully utilize a CPU. 
But in some cases there might be program code, that always needs to be executed **sequentially**.
With stance, such a worker can be executed in the context of the web application.

**examples/flask_with_worker.py**

```python
import os
from flask import Flask
from queue import Queue
from time import sleep
from threading import Thread
from stance import Stance

app = Flask('stance-example')


@app.route('/work-for/<seconds>', methods=['GET'])
def work(seconds):
    worker.put_task(seconds, 'Work done!')
    return 'Task handed over to worker with PID {}!\n'.format(worker.getpid())


class Worker:
    def __init__(self):
        self._task_queue = None

    def late_init(self):
        self._task_queue = Queue()
        Thread(target=self._do_work_sequentially).start()

    def _do_work_sequentially(self):
        while True:
            seconds, message = self._task_queue.get()
            sleep(int(seconds))
            print(message)

    def put_task(self, seconds, message):
        self._task_queue.put((seconds, message))

    def getpid(self):
        return os.getpid()

s = Stance(clazz=Worker, port=17310)
worker = s.register()

if s.created_new_instance():
    worker.late_init()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

This code can be executed as a single process flask development server.

```bash
python3 examples/flask_with_worker.py
```

Send some work to be executed sequentially.

```bash
curl localhost:5000/work-for/10
curl localhost:5000/work-for/5
```

It is possible to use the same code with a mod_wsgi setup.

**examples/flask_with_worker.wsgi**

```python
import os
import sys

sys.path.insert(0, os.path.split(os.path.abspath(__file__))[0])

from flask_with_worker import app as application
```

Create a new site config for Apache2. It is important to use the `WSGIDaemonProcess` directive and to set
`WSGIApplicationGroup %{GLOBAL}`, because we want the processes to be created once. Every daemon process tries to
connect to the worker or tries to create a new instance, if it is not yet running. They can now use this instance, as
long as the web server is running and it will be terminated when Apache shuts down. The `WSGIImportScript` is a
recommended directive, because it will start the processes and execute the *flask_with_worker.wsgi* script for each
daemon, as soon as Apache starts. Otherwise it would wait for incoming requests.

The web application will be executed with 4 daemon processes, each serving up to 16 requests concurrently. All daemon
processes will share the same worker process.

**/etc/apache2/sites-available/flask_with_worker.conf**

```apache
Listen 5000

<VirtualHost *:5000>
    ServerName localhost

    WSGIDaemonProcess stance-example user=stanceuser group=stanceuser processes=4 threads=16
    WSGIScriptAlias / /PATH/TO/stance/examples/flask_with_worker.wsgi
    WSGIImportScript /PATH/TO/stance/examples/flask_with_worker.wsgi process-group=stance-example application-group=%{GLOBAL}
    WSGIPassAuthorization On

    <Directory /PATH/TO/stance/examples>
        <Files flask_with_worker.wsgi>
            WSGIApplicationGroup %{GLOBAL}
            WSGIProcessGroup stance-example
            Require all granted
       </Files>
    </Directory>
</VirtualHost>
```

Enable the site config and restart apache2. The print output goes to the apache2 error log.

```bash
sudo a2ensite flask_with_worker
sudo service apache2 restart
tail -f /var/log/apache2/error.log
```

Send some work to be executed sequentially.

```bash
curl localhost:5000/work-for/10
curl localhost:5000/work-for/5
```

## Projects using stance

[CC-Server of Curious Containers](https://github.com/curious-containers/cc-server)
