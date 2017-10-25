#!/usr/bin/env python
# coding=utf-8

import click
import xmltodict
import yaml
import logging


class cliconfig(object):

    def __init__(self):
        self.verbose = False

pass_config = click.make_pass_decorator(cliconfig, ensure=True)


def getvar(line, field):
    if field in line:
        return line[field]
    else:
        return None


def byteify(input):
    if isinstance(input, dict):
        return {byteify(key): byteify(value)
                for key, value in input.iteritems()}
    elif isinstance(input, list):
        return [byteify(element) for element in input]
    elif isinstance(input, unicode):
        return input.encode('utf-8')
    else:
        return input


@click.group()
@click.option('-v', '--verbose', count=True)
@pass_config
def cli(config, verbose):
    config.verbose = verbose
    pass


@cli.command()
@click.argument('filename', type=click.File('r'))
@click.argument('results', default='-', type=click.File('w', atomic=True))
@pass_config
def parse(config, filename, results):
    logger = logging.getLogger('parse')
    doc = xmltodict.parse(filename.read())
    ziew = {}
    suffix4 = {}
    suffix6 = {}
    for i in doc['peers']['peer']:
        line = dict(i)
        if 'proto' in line:
            if line['proto'] == 'v6':
                proto = 'ipv6'
            if line['proto'] == 'v4':
                proto = 'ipv4'
        else:
            proto = 'ipv4'
        ip = line['ip']
        asn = line['asn']
        if proto == 'ipv4':
            peer = ip.split('.')[-2:]
            peer = '_'.join(peer)
            suffix = 1
            if peer in suffix4.keys():
                suffix = suffix4[peer] + 1
                suffix4[peer] = suffix
            else:
                suffix4[peer] = suffix
            peer = '{}x{}'.format(peer, suffix)
        if proto == 'ipv6':
            peer = asn
            suffix = 1
            if peer in suffix6.keys():
                suffix = suffix6[peer] + 1
                suffix6[peer] = suffix
            else:
                suffix6[peer] = suffix
            peer = '{}x{}'.format(peer, suffix)
        if config.verbose:
            logger.info('{} {} {}'.format(peer, ip, line['description']))
        peerres = dict(
            description=line['description'],
            ip=ip,
            asn=int(asn)
        )

        if 'multihop' in line and line['multihop'] == 'true':
            peerres['multihop'] = 5
        flags = []
        if 'rs' in line and line['rs'] == 'false':
            flags.append('no-rs')
        if 'prepend' in line and line['prepend'] == 'true':
            flags.append('prepend')
        if 'nh' in line and line['nh'] == 'false':
            flags.append('no-nexthop-check')
        if 'hidden' in line and line['hidden'] == 'true':
            flags.append('hidden')
        if 'disable' in line and line['disable'] == 'true':
            flags.append('disable')
        if 'filter' in line and line['filter'] == 'false':
            flags.append('no-filter')
        if 'passive' in line and line['passive'] == 'false':
            flags.append('no-passive')
        if 'group' in line:
            cfg = []
            groups = line['group']
            if type(groups) is not list:
                groups = [groups]
            for gr in groups:
                cfg.append(gr['@id'])
            peerres['group'] = cfg
        if proto == 'ipv6':
            peerres['proto'] = 'ipv6'
        if 'macro' in line:
            peerres['macro'] = line['macro']
        if not flags == []:
            peerres['flags'] = flags
        ziew[peer] = peerres

    ziew = byteify(ziew)

    Dumper = yaml.Dumper
    Dumper.ignore_aliases = lambda self, data: True
    yaml.dump(ziew, results, Dumper=Dumper, default_flow_style=False)
