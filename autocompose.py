#! /usr/bin/env python

import sys, argparse, pyaml, docker
from collections import OrderedDict


def main():
    parser = argparse.ArgumentParser(description='Generate docker-compose yaml definition from running container.')
    parser.add_argument('-v', '--version', type=int, default=3, help='Compose file version (1 or 3)') 
    parser.add_argument('cnames', nargs='*', type=str, help='The name of the container to process.')
    args = parser.parse_args()

    struct = {}
    networks = []
    for cname in args.cnames:
        cfile, networks = generate(cname)
        struct.update(cfile)

    render(struct, args, networks)


def render(struct, args, networks):
    if args.version == 1:
        pyaml.p(OrderedDict(struct))
    else:
        pyaml.p(OrderedDict({'version': '3', 'services': struct, 'networks': networks}))
    

def _value_valid(value):
    return value and value not in ('null', 'default', ',', 'no')


def get_value_mapping(cattrs):
    mapping = {
        'cap_add': cattrs['HostConfig']['CapAdd'],
        'cap_drop': cattrs['HostConfig']['CapDrop'],
        'cgroup_parent': cattrs['HostConfig']['CgroupParent'],
        'container_name': cattrs['Name'][1:],
        'devices': cattrs['HostConfig']['Devices'],
        'dns': cattrs['HostConfig']['Dns'],
        'dns_search': cattrs['HostConfig']['DnsSearch'],
        'environment': cattrs['Config']['Env'],
        'extra_hosts': cattrs['HostConfig']['ExtraHosts'],
        'image': cattrs['Config']['Image'],
        'labels': cattrs['Config']['Labels'],
        'links': cattrs['HostConfig']['Links'],
        'logging': {
            'driver': cattrs['HostConfig']['LogConfig']['Type'],
            'options': cattrs['HostConfig']['LogConfig']['Config']
        },
        'networks': {
            x: {'aliases': cattrs['NetworkSettings']['Networks'][x]['Aliases']}
            for x in cattrs['NetworkSettings']['Networks'].keys()
        },
        'security_opt': cattrs['HostConfig']['SecurityOpt'],
        'ulimits': cattrs['HostConfig']['Ulimits'],
        'volumes': cattrs['HostConfig']['Binds'],
        'volume_driver': cattrs['HostConfig']['VolumeDriver'],
        'volumes_from': cattrs['HostConfig']['VolumesFrom'],
        'cpu_shares': cattrs['HostConfig']['CpuShares'],
        'cpuset': cattrs['HostConfig']['CpusetCpus'] + ',' + cattrs['HostConfig']['CpusetMems'],
        'entrypoint': cattrs['Config']['Entrypoint'],
        'user': cattrs['Config']['User'],
        'working_dir': cattrs['Config']['WorkingDir'],
        'domainname': cattrs['Config']['Domainname'],
        'hostname': cattrs['Config']['Hostname'],
        'ipc': cattrs['HostConfig']['IpcMode'],
        'mac_address': cattrs['NetworkSettings']['MacAddress'],
        'mem_limit': cattrs['HostConfig']['Memory'],
        'memswap_limit': cattrs['HostConfig']['MemorySwap'],
        'privileged': cattrs['HostConfig']['Privileged'],
        'restart': cattrs['HostConfig']['RestartPolicy']['Name'],
        'read_only': cattrs['HostConfig']['ReadonlyRootfs'],
        'stdin_open': cattrs['Config']['OpenStdin'],
        'tty': cattrs['Config']['Tty']
    }

    try:
        expose_value = list(cattrs['Config']['ExposedPorts'].keys())
        ports_value = [
            cattrs['HostConfig']['PortBindings'][key][0]['HostIp'] + ':' + cattrs['HostConfig']['PortBindings'][key][0][
                'HostPort'] + ':' + key for key in cattrs['HostConfig']['PortBindings']]

        # If bound ports found, don't use the 'expose' value.
        if _value_valid(ports_value):
            for index, port in enumerate(ports_value):
                if port[0] == ':':
                    ports_value[index] = port[1:]

            mapping['ports'] = ports_value
        else:
            mapping['expose'] = expose_value
    except (KeyError, TypeError):
        pass

    return mapping


def build_networks(networks_list, network_keys):
    return {
        network.attrs['Name']: {
            'external': not network.attrs['Internal']
        }
        for network in networks_list if network.attrs['Name'] in network_keys
    }


def build_service(cattrs, value_map):
    service_name = cattrs['Name'][1:]
    return {
        service_name: {
            key: value for key, value in value_map.items() if _value_valid(value)
        }
    }


def generate(cname):
    c = docker.from_env()

    try:
        cid = [x.short_id for x in c.containers.list() if cname == x.name or x.short_id in cname][0]
    except IndexError:
        print("That container is not running.")
        sys.exit(1)

    cattrs = c.containers.get(cid).attrs
    values = get_value_mapping(cattrs)

    return build_service(cattrs, values), build_networks(c.networks.list(), values['networks'].keys())


if __name__ == "__main__":
    main()

