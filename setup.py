from setuptools import setup, find_packages

setup(
    name="docker-autocompose",
    version="1.4.0",
    description="Generate a docker-compose yaml definition from a running container",
    url="https://github.com/Dr4ik/docker-autocompose",
    author="Red5d Dr4ik",
    license="GPLv2",
    keywords="docker yaml container",
    packages=find_packages(),
    install_requires=[
        'pyaml>=17.12.1',
        'docker>=3.4.1',
        'ruamel.yaml>==0.16.5',
        'toolz>=0.10.0'
    ],
    scripts=['bin/docker-autocompose'],
)
