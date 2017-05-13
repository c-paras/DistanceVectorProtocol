#!/usr/bin/python
#Written by Costa Paraskevopoulos in May 2017
#Implements the distance vector routing protocol over UDP
#Python 2.7 has been used (the #! line should default to version 2.7)

import sys, re, os, time, select
from socket import *

DEBUG = 0

def main():

	#get neighbors for this node
	neighbors, num_neighbors = process_config_file(CONFIG_FILE)
	if DEBUG:
		print 'I have', num_neighbors, 'neighbors'
		print 'My neighbors:'
		for n in neighbors:
			print n, get_cost(neighbors, n), get_port(neighbors, n)

	#initialise dist table for this node
	my_dist = initialise_dist(neighbors)
	if DEBUG:
		print 'My dist table:'
		for node in my_dist:
			print 'Via', node + ':', my_dist[node]

	#initialise dv table for this node
	my_dv = initialise_dv(neighbors)
	if DEBUG:
		print 'My DV table:'
		for node in my_dv:
			print node, my_dv[node]

	#create new udp socket for this node
	try:
		sock = socket(AF_INET, SOCK_DGRAM)
		sock.bind(('', my_port()))
	except:
		print >>sys.stderr, sys.argv[0] + ': port', my_port(), 'in use'
		sock.close()
		sys.exit(1)

	last_advert = 0 #node hasn't shared dv yet - set to beginning of time
	dv_changed = {} #tracks whether the last advert from a router changed the dv
	printed_dv = False #ensures a particular stable dv is only printed once
	next_hop = {} #stores the next node in the shortest path to each router

	while 1:
		try:

			#notify neighbors every TIME_BETWEEN_ADVERTS seconds
			current_time = int(time.time())
			if current_time - last_advert > TIME_BETWEEN_ADVERTS:
				last_advert = current_time
				msg = str(my_dv) #TODO
				if DEBUG:
					print my_id(), 'sending:'
					print msg
				for n in neighbors:
					sock.sendto(msg, ('', get_port(neighbors, n)))

			#check if another node has advertised their dv table
			available = select.select([sock], [], [], 0)
			if available[0]:
				data, addr = sock.recvfrom(1024)
				received_dv = process_dv_table(data) #TODO
				if DEBUG:
					print my_id() + ' received from ' + str(addr)
				sender_id = get_node_id(neighbors, addr[1])
				my_dist = recompute_dist(neighbors, my_dist, received_dv, sender_id)
				if DEBUG:
					print 'My dist table:'
					for node in my_dist:
						print 'Via', node + ':', my_dist[node]

				old_dv = my_dv
				my_dv, next_hop = recompute_dv(my_dist)
				if DEBUG:
					print 'My DV table:'
					for node in my_dv:
						print node, my_dv[node]

				#update the change status of the dv from the current sender
				if my_dv != old_dv:
					dv_changed[sender_id] = True
					if printed_dv == True:
						printed_dv = False #allow dv to be printed again
				else:
					dv_changed[sender_id] = False

			#print dv if dv is considered stable; stability is detected when
			#the last advert from all nodes has not changed the dv
			if printed_dv == False and is_dv_stable(neighbors, dv_changed):
				printed_dv = True
				print "Router %s's DV table:" %my_id()
				for node in my_dv:
					print 'shortest path to node %s:' %node,
					print 'the next hop is %s' %next_hop[node],
					print 'and the cost is %.1f' %my_dv[node]

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
				dist[n][m] = float('infinity') #not direct neighbor
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
	for node in received_dv:
		if node == my_id():
			continue
		else:
			my_dist[sender_id][node] = cost_to_sender + received_dv[node]

	return my_dist

#updates the dv table based on the current dist table
#also returns the next hop in the path to each destination
def recompute_dv(my_dist):

	#create a new dv with max cost to all known nodes
	dv = {}
	for n in my_dist:
		dv[n] = float('infinity')
		for m in my_dist[n]:
			dv[m] = float('infinity')

	#select smallest cost to each known node
	next_hop = {}
	for via in my_dist:
		for dest in dv:
			if dest in my_dist[via]:
				if my_dist[via][dest] < dv[dest]:
					dv[dest] = my_dist[via][dest]
					next_hop[dest] = via

	return (dv, next_hop)

#returns True if the dv is stable; False otherwise
def is_dv_stable(neighbors, dv_changed):
	for n in neighbors:
		if not n in dv_changed:
			return False #don't assume anything until at least one advert
		elif dv_changed[n]:
			return False
	return True

#getters
def get_cost(neighbors, node_id):
	return neighbors[node_id][0]
def get_port(neighbors, node_id):
	return neighbors[node_id][1]
def get_node_id(neighbors, port):
	for n in neighbors:
		if neighbors[n][1] == port:
			return n
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
		print >>sys.stderr, "%s: cannot read '%s'" %(sys.argv[0], filename)
		sys.exit(1)

if __name__ == '__main__':

	#require 3 or 4 args
	if len(sys.argv) != 4 and len(sys.argv) != 5:
		args = '<node id> <node port> <config file> [-P]'
		print >>sys.stderr, 'Usage:', sys.argv[0], args
		sys.exit(1)

	#id must be a capital letter
	if not (len(sys.argv[1]) == 1 and sys.argv[1].isupper()):
		print >>sys.stderr, "%s: invalid id '%s'" %(sys.argv[0], sys.argv[1])
		sys.exit(1)

	#port # must be non-negative
	if not sys.argv[2].isdigit():
		print >>sys.stderr, "%s: invalid port number '%s'" %(sys.argv[0], sys.argv[2])
		sys.exit(1)

	NODE_ID = sys.argv[1]
	NODE_PORT = int(sys.argv[2])
	CONFIG_FILE = sys.argv[3]

	#globals
	TIME_BETWEEN_ADVERTS = 5

	main()
