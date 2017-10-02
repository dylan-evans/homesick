#!/usr/bin/env python
import os
import re
import logging
import argparse
from copy import copy
from urlparse import urlparse
from logging import debug, info, error

import yaml
import pystache
from paramiko.client import SSHClient, WarningPolicy

DATAPATH = os.path.expanduser("~/.homesick")
CONFPATH = os.path.join(DATAPATH, "config.yaml")


def main(cmd_line):
    logging.basicConfig(level=logging.INFO)
    print cmd_line.config
    with open(cmd_line.config) as src:
        conf = yaml.load(src)

    os.chdir(cmd_line.path)

    cmd_line.handler(cmd_line, conf)


def sync_handler(cmd_line, conf):

    client = SSHClient()
    client.set_missing_host_key_policy(WarningPolicy())

    env = {'$' + key: val for key, val in conf.get('variables', {}).items()}

    for host, tags in conf["hosts"].items():
        url = urlparse(host)
        ctx = {'host:' + host: True}
        if tags:
            ctx.update({'tag:' + tag: True for tag in tags})
        ctx.update(env)
        try:
            client.connect(
                hostname=url.hostname,
                port=url.port or 22,
                username=url.username,
                password=url.password
            )
        except:
            error("Connection failed to '%s'", host)
            continue

        home = url.path if url.path else "./"

        fileset = copy(conf.get("files", {}).get("all", {}))
        for tag in tags:
            fileset.update(conf.get("files", {}).get(tag, {}))

        sftp = client.open_sftp()
        for local, remote in fileset.items():
            info("Uploading '%s' as '%s'", local, remote)
            with open(local) as src:
                with sftp.open(remote, mode="w") as dst:
                    stdout = client.exec_command("echo $HOME")[1]
                    home = stdout.read().strip()
                    dst.write(pystache.render(src.read(), ctx))
        client.close()


def get_arguments():
    main_parser = argparse.ArgumentParser(description="Sync home directories.")
    main_parser.add_argument("--config", "-c", default=CONFPATH)
    main_parser.add_argument("--path", "-p", default=os.getenv("HOMESICKPATH", DATAPATH))

    subparsers = main_parser.add_subparsers()

    sync_parser = subparsers.add_parser('sync')
    sync_parser.set_defaults(handler=sync_handler)

    return main_parser.parse_args()


if __name__ == '__main__':
    main(get_arguments())

