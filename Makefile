venv ?= .env

init: $(venv)
	$(venv)/bin/pip install -r requirements.txt
	$(venv)/bin/runcommand init

$(venv):
	virtualenv -p python3 $(venv)

.PHONY = init
