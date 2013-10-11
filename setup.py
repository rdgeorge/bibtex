#!/usr/bin/env python

from distutils.core import setup

setup(
    name='bibtex',
    version='0.1',
    description='Manipulate BibTeX files',
    long_description=open('README').read(),
    author='Richard George',
    author_email='rdg@roe.ac.uk',
    url='',
    packages=['bibtex'],
    scripts=['bin/pdftobib', 'bin/mnbib'],
)
