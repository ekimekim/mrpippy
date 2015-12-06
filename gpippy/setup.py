from setuptools import setup, find_packages

setup(
	name="gpippy",
	version="0.0.1",
	author="ekimekim",
	author_email="mikelang3000@gmail.com",
	description="Fallout 4 Pip Boy app client and server",
	packages=find_packages(),
	install_requires=[
		'gevent',
	],
)
