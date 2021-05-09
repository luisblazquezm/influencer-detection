#!/usr/bin/python3

# Copyright 2020 Luis Blazquez Miñambres (@luisblazquezm), Miguel Cabezas Puerto (@MiguelCabezasPuerto), Óscar Sánchez Juanes (@oscarsanchezj) and Francisco Pinto-Santos (@gandalfran)
# See LICENSE for details.

import io

from setuptools import setup, find_packages


def readme():
    with io.open('README.md', encoding='utf-8') as f:
        return f.read()

def read_requeriments_file(filename):
    with io.open(filename, encoding='utf-8') as f:
        for line in f.readlines():
            yield line.strip()


setup(
    name='SOA final project API',
    version='1.0',
    packages=find_packages(),
    url='https://github.com/GandalFran/soa-final',
    download_url='https://github.com/GandalFran/soa-final/archive/master.zip',
    license='GNU Affero General Public License v3',
    author='Luis Blazquez Miñambres, Miguel Cabezas Puerto, Óscar Sánchez Juanes and Francisco Pinto-Santos',
    author_email='luisblazquezm@usal.es, miguelcabezaspuerto@usal.es, oscar.sanchez@usal.es and franpintosantos@usal.es',
    description='Flask RESTX API for SOA final project',
    long_description=readme(),
    long_description_content_type='text/markdown',
    install_requires=list(read_requeriments_file('requirements.txt')),
    entry_points={
        'console_scripts': [
            'soa=soa.run:main'
        ],
    },
    include_package_data=True,
    classifiers=[
        "Development Status :: 1 - Alpha",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: GNU Affero General Public License v3",
        "Intended Audience :: Developers"
    ],
    keywords='soa, flask, python',
    python_requires='>=3',
    project_urls={
        'Bug Reports': 'https://github.com/GandalFran/soa-final/issues',
        'Source': 'https://github.com/GandalFran/soa-final',
        'Documentation': 'https://github.com/GandalFran/soa-final'
    },
)