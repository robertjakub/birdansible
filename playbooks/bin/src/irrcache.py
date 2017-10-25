#!/usr/bin/env python
# coding=utf-8

import sys
import os
import yaml
import json
import click
import logging
import subprocess
import irrparser
import ipaddr
try:
    from urllib.request import urlretrieve
except ImportError:
    from urllib import urlretrieve
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

class cliconfig(object):

    def __init__(self):
        self.verbose = False

pass_config = click.make_pass_decorator(cliconfig, ensure=True)


@click.group()
@click.option('-v', '--verbose', count=True, envvar='VERBOSE')
@pass_config
def cli(config, verbose):
    config.verbose = verbose
    pass


@cli.command()
@click.argument('filename', type=click.File('r'))
@click.argument('results', default='-', type=click.File('w', atomic=True))
@click.option('--cache', '-c', multiple=True, type=click.File('r'))
@click.option('--update', '-u', type=click.File('r'))
@click.option('--host', '-h', required=True)
@click.option('--addon', '-a', type=click.File('r'))
@pass_config
def cache(config, cache, update, filename, results, host, addon):
    verbose = config.verbose
    irrcache = {}
    yf = {}
    prefixes = {}
    prefixes6 = {}
    peers = yaml.load(filename, Loader=Loader)
    asns = []
    fasn = {}
    netempty = {}
    hosts = {}
    logger = logging.getLogger('cache')
    cloaded = False
    addons = {}

    if addon is not None:
        try:
            addons = yaml.load(addon, Loader=Loader)
        except:
            addons = None
        if addons is None:
            addons = {}

    if update is not None:
        try:
            fcache = yaml.load(update, Loader=Loader)
        except:
            fcache = None
        if fcache is None:
            fcache = {}
        fasn = fcache['macros'] if 'macros' in fcache else {}
        asns = fcache['asn'] if 'asn' in fcache else []
        prefixes = fcache['prefixes'] if 'prefixes' in fcache else {}
        netempty = fcache['skip'] if 'skip' in fcache else {}
        yf['host'] = fcache['host'] if 'host' in fcache else {}

    for fn in cache:
        try:
            tc = yaml.load(fn, Loader=Loader)
        except:
            tc = None
        if tc is None:
            tc = {}
        for pr in tc.keys():
            tmp = irrcache[pr] if pr in irrcache else {}
            irrcache[pr] = dict(tmp, **tc[pr])
        cloaded = True

    for p in peers:
        peer = peers[p]
        logmsg = 'peer: {}'.format(p)
        if verbose > 1:
            logger.info(logmsg)
        if 'macro' in peer:
            if 'flags' in peer and 'no-filter' in peer['flags']:
                continue
            if peer['macro'] not in fasn:
                irr = peer['irr'] if 'irr' in peer else 'RIPE'
                logmsg = 'macro/asn: {}'.format(peer['macro'])
                if verbose > 2:
                    logger.info(logmsg)
                cmd = ['bgpq3', '-S{}'.format(irr)]
                cmd = cmd + ['-3jlasn', '-f 1', peer['macro']]
                output = subprocess.check_output(cmd)
                asn = json.loads(output)
                ptasn = asn['asn']
                if 'macro' in addons and peer['macro'] in addons['macro']:
                    for a in addons['macro'][peer['macro']]:
                        ptasn.append(a)
                fasn[peer['macro']] = list(set(ptasn))
                for a in asn['asn']:
                    asns.append(a)
                if 'macro' in addons and peer['macro'] in addons['macro']:
                    for a in addons['macro'][peer['macro']]:
                        asns.append(a)
    asns = list(set(asns))
    yf['macros'] = fasn
    yf['asn'] = asns

    for p in peers:
        peer = peers[p]
        if 'macro' in peer:
            logmsg = 'peer: {} {}'.format(p, peer['macro'])
            if verbose > 1:
                logger.info(logmsg)
            mtype = peer['proto'] if 'proto' in peer else 'ipv4'
            if 'flags' in peer and 'no-filter' in peer['flags']:
                continue
            mcmd = '-4' if mtype == 'ipv4' else '-6'
            if peer['macro'] in fasn:
                macro = fasn[peer['macro']]
            else:
                continue
            prefix = prefixes[mtype] if mtype in prefixes else {}
            phost = hosts[mtype] if mtype in hosts else []
            if 'prefixes' in addons and mtype in addons['prefixes']:
                pnetcache = addons['prefixes'][mtype]
            else:
                pnetcache = {}
            ne = netempty[mtype] if mtype in netempty else []
            for a in macro:
                if a in prefix:
                    phost.append(a)
                    continue
                cmd = 'prefix: {} {}'.format(mtype, a)
                irr = peer['irr'] if 'irr' in peer else 'RIPE'
                pnets = []
                if str(a) in ['23456']:
                    if verbose > 2:
                        logger.info('{} skipped (forbidden)'.format(cmd))
                    continue
                if a in pnetcache:
                    pnets = pnets + pnetcache[a]
                    phost.append(a)
                if cloaded and irr == 'RIPE' and mtype in irrcache:
                    if a not in irrcache[mtype] and pnets == []:
                        if verbose > 2:
                            logger.info('{} skipped (not in irr)'.format(cmd))
                        continue
                if a in ne:
                    if verbose > 2:
                        logger.info('{} skipped (empty)'.format(cmd))
                    continue

                if mtype in irrcache and a in irrcache[mtype]:
                    if verbose > 2:
                        logger.info('{} irrcache'.format(cmd))
                    phost.append(a)
                    pnets = pnets + irrcache[mtype][a]
                else:
                    if verbose > 2:
                        logger.info('{} bgpq3'.format(cmd))
                    cmd = ['bgpq3', '-S{}'.format(irr)]
                    cmd = cmd + [mcmd, '-3jlnet', "AS{}".format(a)]
                    output = subprocess.check_output(cmd)
                    pr = json.loads(output)['net']
                    if len(pr) == 0 and pnets == []:
                        logmsg = 'wrong {} prefix!!! {}'.format(mtype, a)
                        if verbose > 0:
                            logger.warning(logmsg)
                        ne = netempty[mtype] if mtype in netempty else []
                        ne.append(a)
                        netempty[mtype] = ne
                        continue
                    phost.append(a)
                    for p in pr:
                        pnets.append(p['prefix'])
                pnets = [str(tpr) for tpr in pnets]
                prefix[a] = list(set(pnets))
            prefixes[mtype] = prefix
            hosts[mtype] = list(set(phost))
    yf['prefixes'] = prefixes
    yf['skip'] = netempty
    yf['host'][str(host)] = hosts

    Dumper = yaml.Dumper
    Dumper.ignore_aliases = lambda self, data: True
    yaml.dump(yf, results, Dumper=Dumper, default_flow_style=False)
    return 0


@cli.command()
@click.option('--v4/--v6')
@click.argument('filename', type=click.File('r'))
@click.argument('results', default='-', type=click.File('w', atomic=True))
@pass_config
def irr(config, v4, filename, results):
    object_data = []
    ziew = {}
    for line in filename.readlines():
        if not line == '\n':
            object_data.append(line)
        else:
            obj, values = irrparser.irrParser(object_data)
            object_data = []

            if obj == irrparser.ROUTE:
                try:
                    ipaddr.IPNetwork(values[0], strict=True)
                except ValueError as e:
                    if 'does not appear to be' in str(e):
                        pass  # usually leading zero in v4 octets, we can handle those
                    else:
                        print >> sys.stderr, str(e), 'source: ', values[2]
                        continue
                asn = values[1]
                entry = ziew[asn] if asn in ziew else []
                entry.append(values[0])
                ziew[asn] = entry

    retval = {}
    proto = 'ipv4' if v4 else 'ipv6'
    retval[proto] = ziew
    Dumper = yaml.Dumper
    Dumper.ignore_aliases = lambda self, data: True
    yaml.dump(retval, results, Dumper=Dumper, default_flow_style=False)
