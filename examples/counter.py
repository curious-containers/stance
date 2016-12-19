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

s = Stance(_class=Counter, port=17310, secret='PASSWORD')
counter = s.register(start_value=100)

if s.created_new_instance():
    print('enter infinite loop...')
    while True:
        sleep(1)

counter.increment()
print(counter.get_count())
