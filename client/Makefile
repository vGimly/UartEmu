.PHONY: client test
socat:=socat
uart_host:=10.9.0.1
uart_port:=7000
uart_tty:=./uart0

client:
	screen -dmS cli \
	$(socat) PTY,link=$(uart_tty),raw,echo=0 TCP:$(uart_host):$(uart_port)

test:
	echo hello > $(uart_tty)