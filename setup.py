#!/usr/bin/env python3

from distutils.core import setup

setup(
    name='stance',
    version='1.0',
    summary='stance provides self-instantiating worker processes for Python 3',
    description='stance provides self-instantiating worker processes for Python 3. It is best used with WSGI applications, like a flask web server, where the forking of processes takes place, before the user gains control.',
    author='Christoph Jansen',
    author_email='christoph@gnork.org',
    url='https://github.com/curious-containers/stance',
    packages=['stance'],
    license='MIT',
    platforms=['any'],
    install_requires=[]
)
