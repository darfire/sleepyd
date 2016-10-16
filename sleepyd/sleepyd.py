import os
import sys
import glob
import select
import datetime
import configparser
import argparse
import syslog

from pep3143daemon import DaemonContext, PidFile


SUSPEND_INTERVAL = 30
RELOAD_INTERVAL = 30
KEYWORDS = ('mice', 'mouse', 'kbd')
SUSPEND_COMMAND = 'pm-suspend'


def fdopen(fname):
  fd = os.open(fname, os.O_RDONLY)
  os.set_blocking(fd, False)

  return fd


def read_all(fd):
  while True:
    data = os.read(fd, 1024)

    if len(data) < 1024:
      return


def get_mouse_kbd_event_files():
  fname = glob.glob('/dev/input/by-path/*')

  result = []

  for f in fname:
    for k in KEYWORDS:
      if k in f:
        result.append(f)

  result = list(set(result))

  fds = list(map(fdopen, result))

  return fds


def check_tcp_ports_ok(expected):
  tcp_ports = set(expected)
  with open('/proc/net/tcp') as f:
    lines = list(map(lambda x: x.split(), f.readlines()))

    lines = [x for x in lines if x[3] == '01']

    local_addresses = [x[1] for x in lines]
    ports = [x.split(':')[1] for x in local_addresses]

    ports = set(int('0x' + x, 0) for x in ports)

    print('Got ports {} vs {}'.format(ports, tcp_ports))

    return len(ports & tcp_ports) == 0


def main_loop(args):
  config = configparser.ConfigParser()

  config.read(args.config)

  reload_interval = int(config['main'].get('reload_interval', RELOAD_INTERVAL))
  suspend_interval = int(
    config['main'].get('suspend_interval', SUSPEND_INTERVAL))
  suspend_command = config['main'].get('suspend_command', SUSPEND_COMMAND)
  tcp_ports = config['main'].get('tcp_ports', '')

  tcp_ports = list(map(lambda x: int(x.strip()), tcp_ports.split(',')))

  last_touched = datetime.datetime.now()
  irl = get_mouse_kbd_event_files()
  last_reloaded = datetime.datetime.now()

  while True:
    (orl, _, _) = select.select(irl, [], [], 10)

    print('Select orl: {}'.format(orl))

    now = datetime.datetime.now()

    if (now - last_reloaded).seconds > reload_interval:
      print('Reloading')
      for fd in irl:
        os.close(fd)

      irl = get_mouse_kbd_event_files()

      last_reloaded = now

      continue

    if len(orl) > 0:
      last_touched = now
      for fd in orl:
        try:
          read_all(fd)
        except Exception as e:
          print('Exception when reading {}: {}'.format(fd, e))

    elif (now - last_touched).seconds > suspend_interval:
      if check_tcp_ports_ok(tcp_ports):
        ret = os.system(suspend_command)
        if ret == 0:
          last_touched = datetime.datetime.now()


def parse_args(argv):
  parser = argparse.ArgumentParser()

  parser.add_argument(
    '-c', '--config', type=str, default='/etc/default/sleepyd.conf')
  parser.add_argument(
    '-p', '--pid-file', default='/tmp/sleepyd.pid')
  parser.add_argument(
    '-n', '--no-daemon', action='store_false', dest='daemonize', default=True)

  return parser.parse_args(argv)


def main():
  args = parse_args(sys.argv[1:])

  if args.daemonize:
    pidfile = PidFile(args.pid_file)
    daemon = DaemonContext(pidfile=pidfile)
    syslog.syslog('Daemonizing')
    daemon.open()

  syslog.syslog('Daemonized')

  main_loop(args)


if __name__ == '__main__':
  main()
