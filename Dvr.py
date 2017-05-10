#!/usr/bin/python
#Written by Costa Paraskevopoulos in May 2017
#Implements the distance vector routing protocol over UDP
#Python 2.7 has been used (the #! line should default to version 2.7)

import sys, re, os, time, select
from socket import *

DEBUG = 1

def main():

	#get neighbors for this node
	neighbors, num_neighbors = process_config_file(CONFIG_FILE)
	if DEBUG:
		print 'My neighbors:'
		print num_neighbors
		for n in neighbors:
			print n, get_cost(neighbors, n), get_port(neighbors, n)

	#initialise dist table for this node
	my_dist = initialise_dist(neighbors)
	if DEBUG:
		print 'My dist table:'
		for node in my_dist:
			print node, my_dist[node]

	#initialise dv table for this node
	my_dv = initialise_dv(neighbors)
	if DEBUG:
		print 'My DV table:'
		for node in my_dv:
			print node, my_dv[node]

	sys.exit(0) #TODO

	#create new udp socket for this node
	try:
		sock = socket(AF_INET, SOCK_DGRAM)
		sock.bind(('', my_port()))
	except:
		print >>sys.stderr, sys.argv[0] + ': port', my_port(), 'in use'
		sock.close()
		sys.exit(1)

	last_advert = 0 #node hasn't shared dv yet - set to beginning of time

	while 1:
		try:

			#notify neighbors every 5 seconds
			current_time = int(time.time())
			if current_time - last_advert > 5:
				last_advert = current_time
				msg = str(my_dv) #TODO
				if DEBUG:
					print msg
				for n in neighbors:
					sock.sendto(msg, ('', get_port(neighbors, n)))

			#check if another node has advertised their dv table
			available = select.select([sock], [], [], 0)
			if available[0]:
				data, addr = sock.recvfrom(1024)
				received_dv = process_dv_table(data) #TODO
				sender_id = get_id(addr) #TODO
				my_dist = recompute_dist(neighbors, my_dist, received_dv, sender_id)
				my_dv = recompute_dv(my_dist, my_dv)

		except KeyboardInterrupt:
			sock.close()
			sys.exit(0)

"""
8 wait (until A sees a link cost change to neighbor V /* case 1 */
9 or until A receives mindist(V,*) from neighbor V) /* case 2 */
10 if (c(A,V) changes by +/-d) /* case 1 */
11 for all destinations Y do
12 distV(A,Y) = distV(A,Y) +/- d
13 else /* case 2: */
14 for all destinations Y do
15 distV(A,Y) = c(A,V) + mindist(V, Y);
16 update mindist(A,*)
15 if (there is a change in mindist(A, *))
16 send mindist(A, *) to all neighbors
17 forever
"""

#returns initial dist table based on the direct neighbors
def initialise_dist(neighbors):
	dist = {}
	for n in neighbors:
		dist[n] = {}
		for m in neighbors:
			if n == m:
				dist[n][m] = get_cost(neighbors, m)
			else:
				dist[n][m] = float("infinity") #not direct neighbor
	return dist

#returns initial dv table based on the direct neighbors
def initialise_dv(neighbors):
	dv = {}
	for n in neighbors:
		dv[n] = get_cost(neighbors, n)
	return dv

#converts a received message into a dictionary
def process_dv_table(msg):
	return eval(msg) #TODO

#updates the dist table based on the received dv table
def recompute_dist(neighbors, my_dist, received_dv, sender_id):
	cost_to_sender = get_cost(neighbors, sender_id)

	#update costs via this sender
	for node in my_dist[sender_id]:
		if node in received_dv:
			my_dist[sender_id][node] = cost_to_sender + received_dv[node]
		else:
			my_dist[sender_id][node] = 0 #TODO

#updates the dv table based on the current dist table
def recompute_dv(my_dist, my_dv):
	pass #TODO

	known_nodes = []
	for n in dist:
		known_nodes.append(n)
		for m in dist:
			if not m in known_nodes:
				known_nodes.append(m)
	for n in dist:
		pass #TODO

	return dv

#getters
def get_cost(neighbors, node_id):
	return neighbors[node_id][0]
def get_port(neighbors, node_id):
	return neighbors[node_id][1]
def my_id():
	return NODE_ID
def my_port():
	return NODE_PORT

#processes the config file
#returns a dictionary of neighbors in the form (cost, port)
#also returns the number of neighbors
def process_config_file(filename):
	if os.access(filename, os.R_OK) and os.path.isfile(filename):
		lines = open(filename, 'r').readlines()
		neighbors = {}
		first_line = 0
		num_neighbors = 0
		for line in lines:
			if first_line == 0:
				line = line.rstrip('\n')
				num_neighbors = int(line)
				first_line = 1
				continue
			line = line.strip('\n')
			(node_id, cost, node_port) = line.split(' ')
			neighbors[node_id] = (float(cost), int(node_port))
		return (neighbors, num_neighbors)
	else:
		print >>sys.stderr, sys.argv[0] + ': cannot read', filename
		sys.exit(1)

if __name__ == '__main__':

	#require 3 or 4 args
	if len(sys.argv) != 4 and len(sys.argv) != 5:
		args = "<node id> <node port> <config file> [-P]"
		print >>sys.stderr, 'Usage:', sys.argv[0], args
		sys.exit(1)

	#id must be a capital letter
	if not (len(sys.argv[1]) == 1 and sys.argv[1].isupper()):
		print >>sys.stderr, sys.argv[0] + ': invalid id'
		sys.exit(1)

	#port # must be non-negative
	if not sys.argv[2].isdigit():
		print >>sys.stderr, sys.argv[0] + ': invalid port number'
		sys.exit(1)

	NODE_ID = sys.argv[1]
	NODE_PORT = int(sys.argv[2])
	CONFIG_FILE = sys.argv[3]

	main()
