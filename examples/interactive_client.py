
import gevent.monkey
gevent.monkey.patch_all()

from code import InteractiveConsole
import logging

from gevent.fileobject import FileObject

from gpippy import Client
from mrpippy.data import Player, Inventory

console = None
client = None


def main(host, level='INFO', interval='5'):
	global client
	interval = float(interval)
	logging.basicConfig(level=level)
	client = Client(host, on_update=on_update)
	client.wait()


def on_update(value):
	logging.debug("Updated value: {}".format(value))
	if value.manager.root and not console:
		gevent.spawn(run_console)


def run_console():
	global console
	sys.stdin = FileObject(sys.stdin)
	console = InteractiveConsole({
		'client': client,
		'player': Player(client.pipdata),
		'inv': Inventory(client.pipdata),
	})
	console.interact()


if __name__ == '__main__':
	import sys
	main(*sys.argv[1:])
