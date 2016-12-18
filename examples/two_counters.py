import os
import sys
from time import sleep

sys.path.insert(0, os.path.split(os.path.split(os.path.abspath(__file__))[0])[0])

from stance import Stance


class Counter:
    def __init__(self, start_value=0):
        self._count = start_value

    def increment(self):
        self._count += 1

    def get_count(self):
        return self._count

    def getpid(self):
        return os.getpid()


s1 = Stance(clazz=Counter, port=17310)
counter1 = s1.register()

s2 = Stance(clazz=Counter, port=17311)
counter2 = s2.register(start_value=100)

if s1.created_new_instance():
    print('enter infinite loop...')
    while True:
        sleep(1)

counter1.increment()

counter2.increment()
counter2.increment()

print('script PID: {}\ncounter1 PID: {} | value: {}\ncounter2 PID: {} | value: {}'.format(
    os.getpid(), counter1.getpid(), counter1.get_count(), counter2.getpid(), counter2.get_count())
)
