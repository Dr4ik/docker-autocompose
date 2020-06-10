import io
import re

import docker
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
from toolz import get

y = YAML(typ='rt')
y.default_flow_style = False
y.sort_base_mapping_type_on_output = False
y.indent(offset=2)


def render(container_names, version=3):
    struct = {}
    networks = []

    for cname in container_names:
        cfile, networks = _generate(cname)
        struct.update(cfile)

    with io.StringIO() as buffer:
        if version == 1:
            y.dump(CommentedMap(struct), buffer)
        elif version == 3:
            d = CommentedMap({'version': '3', 'services': struct})

            if networks:
                d.update({'networks': networks})

            y.dump(d, buffer)
        else:
            raise NotImplementedError('Not implemented for version {}'.format(version))

        return buffer.getvalue()


def _value_valid(value):
    return value and value not in ('null', 'default', ',', 'no')


def convert(key, val):
    def _networks(attrs):
        return {
            network_name: {'aliases': attrs[network_name]['Aliases']}
            for network_name in attrs.keys()
            if attrs[network_name]['Aliases']
        }

    def _cmd(attrs):
        cmd = y.seq(map(str, attrs))
        cmd.fa.set_flow_style()
        return cmd

    def _links(attrs):
        if not attrs:
            return None
        
        match = re.compile(r'/(\w+):/(\w+)/(\w+)').match(attr)

        if not match:
            return None
        
        return [
            '{}:{}'.format(
                *get([0, 2], match.groups())
            )
            for attr in attrs
        ]

    def _devices(attrs):
        return ['{}:{}'.format(*get(['PathOnHost', 'PathInContainer'], dev)) for dev in attrs]

    f = {
        'command': _cmd,
        'devices': _devices,
        'links': _links,
        'networks': _networks
    }.get(key)

    if not callable(f):
        return val

    if not val:
        return val

    return f(val)


def _get_value_mapping(cattrs):
    mapping = {
        'command': cattrs['Config']['Cmd'],
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
        'networks': cattrs['NetworkSettings']['Networks'],
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

    mapping = { k: convert(k, v) for k, v in mapping.items() }

    def _ports(attrs):
        if not attrs:
            return None

        return [
            "{}:{}:{}".format(attrs[key][0]['HostIp'], attrs[key][0]['HostPort'], key)
            for key in attrs
        ]


    try:
        expose_value = list(cattrs['Config']['ExposedPorts'].keys())
        ports_value = _ports(cattrs['HostConfig']['PortBindings'])

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


def _build_networks(networks_list, network_keys):
    return {
        network.attrs['Name']: {
            'external': not network.attrs['Internal']
        }
        for network in networks_list if network.attrs['Name'] in network_keys
    }


def _build_service(cattrs, value_map):
    service_name = cattrs['Name'][1:]
    return {
        service_name: {
            key: value for key, value in value_map.items() if _value_valid(value)
        }
    }


def _generate(cname):
    c = docker.from_env()

    try:
        cid = [x.short_id for x in c.containers.list() if cname == x.name or x.short_id in cname][0]
    except IndexError:
        raise RuntimeError('Container with name or id "{}" is not running'.format(cname))

    cattrs = c.containers.get(cid).attrs
    values = _get_value_mapping(cattrs)

    return _build_service(cattrs, values), _build_networks(c.networks.list(),
                                                           cattrs['NetworkSettings']['Networks'].keys())
