#!/usr/bin/env python
# coding=utf-8

from setuptools import setup, find_packages


package_name = 'aiocrawler'


def get_requires():
    try:
        with open('requirements.txt', 'r') as f:
            requires = [i.split(' ')[0] for i in map(lambda x: x.strip(), f.readlines())
                        if i and i[0] not in ['#', '-']]
        return requires
    except IOError:
        return []


def get_long_description():
    try:
        with open('README.md', 'r') as f:
            return f.read()
    except IOError:
        return ''


pkgs = []
for i in find_packages():
    pkgs.append(i)


setup(
    # license='License :: OSI Approved :: MIT License',
    name=package_name,
    version='0.1.0',
    author='',
    author_email='',
    description='',
    url='',
    long_description=get_long_description(),
    packages=pkgs,
    # Or if it's a single file package
    install_requires=get_requires(),
    py_modules=[package_name],
    entry_points='''
        [console_scripts]
        aiocrawler=aiocrawler:main
    '''
)
