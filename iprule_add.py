import pyroute2
iproute = pyroute2.IPRoute()
iproute.rule('add', 14, 32004, src='10.20.30.40')
