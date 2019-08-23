# docker-autocompose
Generates a docker-compose yaml definition from a running container.

This is a fork of [Red5d/docker-autocompose](https://github.com/Red5d/docker-autocompose) I've just refactored it and shamelessly
added myself as co-author :).

Required Modules:
* [pyaml](https://pypi.python.org/pypi/pyaml/)
* [docker-py](https://pypi.python.org/pypi/docker-py)

Installation:
You can install it dirrectly from github:

    pip install git+https://github.com/Dr4ik/docker-autocompose.git

Example Usage:

    sudo docker-autocompose <container-name-or-id>


Generate a compose file for multiple containers together:

    sudo docker-autocompose apache-test mysql-test


The script defaults to outputting to compose file version 3, but use "-v 1" to output to version 1:

    sudo docker-autocompose -v 1 apache-test


Outputs a docker-compose compatible yaml structure:

[docker-compose reference](https://docs.docker.com/compose/)

[docker-compose yaml file specification](https://docs.docker.com/compose/compose-file/)

While experimenting with various docker containers from the Hub, I realized that I'd started several containers with complex options for volumes, ports, environment variables, etc. and there was no way I could remember all those commands without referencing the Hub page for each image if I needed to delete and re-create the container (for updates, or if something broke).

With this tool, I can easily generate docker-compose files for managing the containers that I've set up manually.

## Docker Usage

You can use this tool from a docker container without installing it locally by either building it or using the [automated build on dockerhub.](https://hub.docker.com/r/red5d/docker-autocompose/)

Build the container by running:

    docker build -t red5d/docker-autocompose .

Use the new image to generate a docker-compose file from a running container or a list of space-separated container names or ids:

     docker run --rm -v /var/run/docker.sock:/var/run/docker.sock red5d/docker-autocompose <container-name-or-id> <additional-names-or-ids>...

