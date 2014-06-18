from setuptools import setup, find_packages

setup(
    name='doublewrap',
    version='0.1',
    packages=find_packages(),
    test_suite='test',

    author='Steven Tilley II',
    author_email='steventilleyii@gmail.com',
    description='A simple wrapper for duplicity that allows a user to save their settings in a config file',
    license='GPLv3'
)
