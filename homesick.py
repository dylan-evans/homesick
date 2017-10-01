#!/usr/bin/env python
import os
import re
import argparse

import yaml
import pystache
from paramiko.client import SSHClient, WarningPolicy

DATAPATH = os.path.expanduser("~/.homesick")
CONFPATH = os.path.join(DATAPATH, "config.yaml")


def main(cmd_line):
    with open(cmd_line.config) as src:
        conf = yaml.load(src)
        print conf

    os.chdir(cmd_line.data)

    cmd_line.handler(cmd_line, conf)


def sync_handler(cmd_line, conf):

    client = SSHClient()
    client.set_missing_host_key_policy(WarningPolicy())

    env = {'$' + key: val for key, val in conf.get('variables', {}).items()}

    for host, tags in conf["hosts"].items():
        ctx = {'host:' + host: True}
        if tags:
            ctx.update({'tag:' + tag: True for tag in tags})
        ctx.update(env)
        try:
            client.connect(host)
            stdin, stdout, stderr = client.exec_command("echo $HOME")
            home = stdout.read().strip()

            sftp = client.open_sftp()

            for local, remote in conf["files"].items():
                with open(local) as src:
                    with sftp.open(remote.replace("~", home), mode="w") as dst:
                        stdout = client.exec_command("echo $HOME")[1]
                        home = stdout.read().strip()
                        dst.write(pystache.render(src.read(), ctx))
            client.close()
        except:
            print "Update failed for '{}'".format(host)


def get_arguments():
    main_parser = argparse.ArgumentParser(description="Sync home directories.")
    main_parser.add_argument("--config", "-c", default=CONFPATH)
    main_parser.add_argument("--data", "-d", default=DATAPATH)

    subparsers = main_parser.add_subparsers()

    sync_parser = subparsers.add_parser('sync')
    sync_parser.set_defaults(handler=sync_handler)

    return main_parser.parse_args()


if __name__ == '__main__':
    main(get_arguments())

