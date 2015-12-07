
import gevent.monkey
gevent.monkey.patch_all()

import json
import logging
import os

from gpippy import Client


def main(host, outfile, level='INFO', interval='5'):
	interval = float(interval)
	logging.basicConfig(level=level)
	client = Client(host, on_update=on_update)
	while not client.finished.ready():
		gevent.sleep(interval)
		if client.pipdata.root:
			if os.path.exists(outfile):
				os.rename(outfile, '{}.tmp'.format(outfile))
			with open(outfile, 'w') as f:
				f.write(json.dumps(client.pipdata.root.value, indent=4) + '\n')
	client.wait()


def on_update(value):
	logging.info("Updated value: {}".format(value))


if __name__ == '__main__':
	import sys
	main(*sys.argv[1:])
