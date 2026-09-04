.PHONY: run start stop kill restart test verify nginx status

app:=main
host:=127.0.0.1
port:=8000

python:=.venv/bin/python
uvicorn:=.venv/bin/uvicorn

run:
	$(uvicorn) $(app):app --host $(host) --port $(port)

dev:
	$(uvicorn) $(app):app --host $(host) --port $(port) --reload

start:
	screen -mS uart-emu $(MAKE) run

stop kill:
	screen -S uart-emu -X quit

restart: stop start

status:
	screen -list | grep '[.]uart-emu' || true

verify:
	$(python) -c 'import main'

test:
	$(python) -m pytest

nginx:
	sudo nginx -s reload
