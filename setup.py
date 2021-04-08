from setuptools import setup, find_packages

DESCRIPTION = 'Monitor new releases by a specified list of artists and auto download using the deemix library'
LONG_DESCRIPTION = DESCRIPTION

# Setting up
setup(
    name='deemon',
    version='0.1.1',
    author='digitalec',
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    packages=['deemon'],
    install_requires=['deemix'],
    url='https://github.com/digitalec/deemon',
    entry_points = {
        'console_scripts': ['deemon=deemon.deemon:main'],
    }
)
