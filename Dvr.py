#!/usr/bin/python
#Written by Costa Paraskevopoulos in May 2017
#Implements the distance vector routing protocol over UDP
#Python 2.7 has been used (the #! line should default to version 2.7)

import sys, re, os, time, select, collections
from socket import *

DEBUG = 0

def main():

	#get neighbors for this node
	neighbors, num_neighbors = process_config_file(CONFIG_FILE)
	if DEBUG:
		print_neighbors(num_neighbors, neighbors)

	#initialise dist table for this node
	my_dist = initialise_dist(neighbors)
	if DEBUG:
		print_dist_table(my_dist)

	#initialise dv table for this node
	my_dv = initialise_dv(neighbors)
	if DEBUG:
		print_dv_table(my_dv)

	#create new UDP socket for this node
	try:
		sock = socket(AF_INET, SOCK_DGRAM)
		sock.bind(('', my_port()))
	except:
		print >>sys.stderr, sys.argv[0] + ': port', my_port(), 'in use'
		sock.close()
		sys.exit(1)

	try:
		main_loop(neighbors, my_dist, my_dv, sock)
	except KeyboardInterrupt:
		sock.close()
		sys.exit(0)

#implements the main logic for the DVR protocol at this router
def main_loop(neighbors, my_dist, my_dv, sock):
	last_advert = 0 #node hasn't shared dv yet - set to beginning of time
	dv_changed = collections.defaultdict(list) #tracks whether the last advert from a router changed the dv
	printed_dv = False #ensures a particular stable dv is only printed once
	next_hop = {} #stores the next node in the shortest path to each router
	heartbeats = collections.defaultdict(int) #tracks # of missed heartbeats from each node
	most_recent_dvs = {} #stores most-recent dv from each neighbor
	dead_routers = []

	while 1:
		dead_neighbors = [] #collects dead routers for later processing
		delayed_dv_adverts = [] #collects dv adverts if they come before heartbeat messages

		#notify neighbors every TIME_BETWEEN_ADVERTS seconds
		current_time = int(time.time())
		if current_time - last_advert > TIME_BETWEEN_ADVERTS:
			last_advert = current_time
			msg = str(my_dv)
			if DEBUG:
				print my_id(), 'sending:'
				print msg
			for n in neighbors:
				sock.sendto(msg, ('', get_port(neighbors, n)))
				data, addr = sock.recvfrom(1024)
				if data.startswith('I am alive!'):
					sender_id = get_node_id(neighbors, addr[1])
					if sender_id == n:
						heartbeats[n] = 0 #node is still alive - reset count
					else:
						heartbeats[sender_id] = 0 #some other node's heartbeat got delayed
						heartbeats[n] += 1
						if heartbeats[n] == KEEP_ALIVE_THRESHOLD:
							dead_neighbors.append(n)
							dead_routers.append(n)
#							if DEBUG:
							print '###########################'
							print "%s's neighbor: router %s died" %(my_id(), n)
							print '###########################'
#					"""
				else:
					delayed_dv_adverts.append((data, addr))
					if get_node_id(neighbors, addr[1]) == n:
						heartbeats[n] = 0 #still alive - due to a dv table advert

		#remove dead routers from dist and dv tables
		for dead in dead_neighbors:
			del neighbors[dead]
			del dv_changed[dead]
			del heartbeats[dead]
			del most_recent_dvs[dead]
			del my_dist[dead]
			for router in my_dist:
				del my_dist[router][dead]
			my_dv, next_hop = recompute_dv(my_dist)
			printed_dv = False #allow dv to be printed again

		#check if a neighboring node has advertised their dv table
#		available = select.select([sock], [], [], 0)
#		if available[0]:
#			data, addr = sock.recvfrom(1024)
		for data, addr in delayed_dv_adverts:
			received_dv = process_dv_table(data, dead_routers)
			sender_id = get_node_id(neighbors, addr[1])

			#update most-recent dv from this neighbor
			if not sender_id in most_recent_dvs:
				most_recent_dvs[sender_id] = received_dv
			else:
				old_most_recent = most_recent_dvs[sender_id]
				most_recent_dvs[sender_id] = received_dv
				dead = infer_dead_routers(old_most_recent, received_dv)
				for d in dead:
#					if DEBUG:
					print '%s knows that %s is dead' %(my_id(), d)
					if d in dead_routers:
						continue #avoid double-printing at the failed router's neighbors
					dead_routers.append(d) #append to list of known dead routers
					printed_dv = False #a router must have died - re-enable printing
					#TODO: modularise & refactor!
					if d in neighbors: del neighbors[d]
					if d in dv_changed: del dv_changed[d]
					if d in heartbeats: del heartbeats[d]
					if d in most_recent_dvs: del most_recent_dvs[d]
					if d in my_dist: del my_dist[d]
					for router in my_dist:
						if d in my_dist[router]: del my_dist[router][d]
					printed_dv = False #allow dv to be printed again

			my_dist = recompute_dist(neighbors, my_dist, received_dv, sender_id)
			old_dv = my_dv
			my_dv, next_hop = recompute_dv(my_dist)

			#update the change status of the dv from the current sender
			if my_dv != old_dv:
				dv_changed[sender_id].append(True)
#				if printed_dv == True:
#					printed_dv = False #allow dv to be printed again
			else:
				dv_changed[sender_id].append(False)

			if DEBUG:
				print my_id() + ' received from ' + str(addr)
				print_dist_table(my_dist)
				print_dv_table(my_dv)

			#send heartbeat msg to sender
			sock.sendto('I am alive!', addr)

		#print dv if dv is considered stable; stability is detected when
		#the last two adverts from all nodes have not changed the dv
		if printed_dv == False and is_dv_stable(neighbors, dv_changed):
			printed_dv = True
			print "Router %s's DV table:" %my_id()
			for node in sorted(my_dv):
				print 'shortest path to node %s:' %node,
				print 'the next hop is %s' %next_hop[node],
				print 'and the cost is %.1f' %my_dv[node]

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

#prints number of neighbors and cost to each neighbor for debugging
def print_neighbors(num_neighbors, neighbors):
	print 'I have', num_neighbors, 'neighbors'
	print 'My neighbors:'
	for n in neighbors:
		print n, get_cost(neighbors, n), get_port(neighbors, n)

#prints dist table for debugging
def print_dist_table(my_dist):
	print 'My dist table:'
	for node in my_dist:
		print 'Via', node + ':', my_dist[node]

#prints dv table for debugging
def print_dv_table(my_dv):
	print 'My DV table:'
	for node in my_dv:
		print node, my_dv[node]

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

#converts a received message into a dictionary, ignoring any dead routers
def process_dv_table(msg, dead_routers):
	dv = eval(msg)
	filtered_dv = {}
	for router_id in dv:
		if not router_id in dead_routers:
			filtered_dv[router_id] = dv[router_id]
	return filtered_dv

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
		elif dv_changed[n][len(dv_changed[n])-1]:
			return False #last dv advert changed this nodes' dv
		elif len(dv_changed[n]) > 1 and dv_changed[n][len(dv_changed[n])-2]:
			return False #2nd-last dv advert changed this nodes' dv
	return True

#returns a list of all routers in the old dv and not the new dv
#this condition implies that the router has failed
#the reverse is not true - if the dv grows, then new router(s) were discovered
def infer_dead_routers(old_most_recent, received_dv):
	dead_nodes = []
	for node in old_most_recent:
		if not node in received_dv:
			dead_nodes.append(node)
	return dead_nodes

#getters
def get_cost(neighbors, node_id):
	return neighbors[node_id][0]
def get_port(neighbors, node_id):
	return neighbors[node_id][1]
def get_node_id(neighbors, port):
	for n in neighbors:
		if neighbors[n][1] == port:
			return n
	return None
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
	KEEP_ALIVE_THRESHOLD = 4

	main()
