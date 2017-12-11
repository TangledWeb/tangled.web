.PHONY = init

init:
	test -d .env || virtualenv -p python3.5 .env
	.env/bin/pip install runcommands
	.env/bin/runcommand init
