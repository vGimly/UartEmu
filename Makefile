.PHONY: run start stop kill restart test verify nginx status test-protocol format check req init

app:=main

req:=requirements.txt
VE:=.venv
VB:=$(VE)/bin
python:=$(VB)/python
uvicorn:=$(VB)/uvicorn
pytest:=$(VB)/pytest
pip:=$(VB)/pip

run:
	$(uvicorn) $(app):app --host 127.0.0.1 --port 8000 $(EXTRA)

dev:
	$(MAKE) run EXTRA=--reload

start:
	screen -mS uart-emu $(MAKE) run

stop kill:
	screen -S uart-emu -X quit

restart: stop start

status:
	screen -list | grep '[.]uart-emu' || true

verify:
	$(python) -c 'import $(app)'

test:
	$(pytest) -v t

nginx:
	sudo nginx -s reload

format:
	$(python) -m black *.py t/*.py t/*/*.py

check:
	$(python) -m black --check *.py t/*.py t/*/*.py

req:
	$(pip) freeze --local > $(req)

init:
	test -x $(python) || python3 -m venv $(VE)
	$(pip) install --proxy http://10.9.0.1:8118 -r $(req)
