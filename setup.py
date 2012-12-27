#!/usr/bin/env python
"""
SafeCalc
---------

Safely evaluate expressions without exec or eval

"""

from setuptools import setup

setup(
    name='safecalc',
    version='0.0.1',
    url='http://github.com/thadeusb/safecalc',
    license='BSD',
    author='Thadeus Burgess',
    author_email='thadeusb@thadeusb.com',
    description='Safely evaluate expressions without eval or exec',
    long_description=__doc__,
    py_modules=[
        'safecalc',
    ],
    zip_safe=False,
    platforms='any',
    install_requires=[
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ]
)
