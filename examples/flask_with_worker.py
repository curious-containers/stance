import os
import sys
from flask import Flask
from queue import Queue
from time import sleep
from threading import Thread

sys.path.insert(0, os.path.split(os.path.split(os.path.abspath(__file__))[0])[0])

from stance import Stance

app = Flask('stance-example')


@app.route('/work-for/<seconds>', methods=['GET'])
def work(seconds):
    worker.put_task(int(seconds), 'Work done!')
    return 'Task handed over to worker with PID {}!'.format(worker.getpid())


class Worker:
    def __init__(self):
        self._task_queue = None

    def late_init(self):
        """
        The late_init function must be executed after the process forking has been done,
        in order to correctly instantiate the Queue and Thread objects in the new process.
        This function must be executed exactly once and only by the process that created the worker instance.

        :return: None
        """
        self._task_queue = Queue()
        Thread(target=self._do_work_sequentially, args=()).start()

    def _do_work_sequentially(self):
        while True:
            seconds, message = self._task_queue.get()
            sleep(seconds)
            print(message)

    def put_task(self, seconds, message):
        self._task_queue.put((seconds, message))

    def getpid(self):
        return os.getpid()

s = Stance(_class=Worker, port=17310)
worker = s.register()

if s.created_new_instance():
    # Execute late_init only once in the process that created the worker instance.
    worker.late_init()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
