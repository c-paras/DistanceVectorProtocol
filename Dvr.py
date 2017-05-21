#!/usr/bin/python
#Written by Costa Paraskevopoulos in May 2017
#Implements the distance vector routing protocol over UDP
#Python 2.7 has been used (the #! line should default to version 2.7)

import sys, re, os, time, select, collections, copy
from socket import *

DEBUG = 0

def main():

	#get neighbors for this node
	neighbors, neighbors2, num_neighbors = process_config_file(CONFIG_FILE)
	if DEBUG:
		print_neighbors(num_neighbors, neighbors)
		print_neighbors(num_neighbors, neighbors2)

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
		main_loop(num_neighbors, neighbors, neighbors2, my_dist, my_dv, sock)
	except KeyboardInterrupt:
		sock.close()
		sys.exit(0)

#implements the main logic for the DVR protocol at this router
def main_loop(num_neighbors, neighbors, neighbors2, my_dist, my_dv, sock):
	last_advert = 0 #node hasn't shared dv yet - set to beginning of time
	printed_dv = False #ensures a particular stable dv is only printed once

	#tracks whether the last advert from a router changed the dv
	dv_changed = collections.defaultdict(list)

	next_hop = {} #next node in the shortest path to each router
	most_recent_dvs = {} #most-recent dv from each neighbor
	dead_routers = [] #all known dead routers
	last_heartbeat = {} #timestamp of last heartbeat from each node

	#node just came alive - set all last heartbeats to current time
	for n in neighbors:
		last_heartbeat[n] = int(time.time())

	#delays the detection of stability in the case of failed nodes being detected or link costs changes
	#this ensures that a router receives updated info from all nodes before claiming stability
	stability_delay = 0

	link_cost_changed = False #to ensure link cost changes only once
	poison_delay = POISON_DELAY #avoid link cost change being applied before all routers have detected stability

	while 1:
		#check if a neighboring node has advertised their dv table
		available = select.select([sock], [], [], 0)
		if available[0]:
			data, addr = sock.recvfrom(1024)
			received_dv = process_dv_table(data, dead_routers)
			sender_id = get_node_id(neighbors, addr[1])
			last_heartbeat[sender_id] = int(time.time())

			#update most-recent dv from this neighbor
			if not sender_id in most_recent_dvs:
				most_recent_dvs[sender_id] = received_dv
			else:
				old_most_recent = most_recent_dvs[sender_id]
				most_recent_dvs[sender_id] = received_dv
				deduced_dead = infer_dead_routers(old_most_recent, received_dv)
				for dead in deduced_dead:
					stability_delay += STABILITY_DELAY
					dv_changed = collections.defaultdict(list)
					if DEBUG:
						print '%s knows that %s is dead' %(my_id(), dead)
					if dead in dead_routers:
						continue #avoid double-printing at the failed router's neighbors
					dead_routers.append(dead) #append to list of known dead routers
					printed_dv = False #a router must have died - re-enable printing
					forget_dead_router(dead, neighbors, dv_changed, last_heartbeat, next_hop, most_recent_dvs, my_dist)

			my_dist = recompute_dist(neighbors, my_dist, received_dv, sender_id)
			old_dv = my_dv
			my_dv, next_hop = recompute_dv(my_dist)

			#update the change status of the dv from the current sender
			if my_dv != old_dv:
				dv_changed[sender_id].append(True)
			else:
				dv_changed[sender_id].append(False)

			if DEBUG:
				print my_id() + ' received from ' + str(addr)
				print_dist_table(my_dist)
				print_dv_table(my_dv)

		dead_neighbors = [] #collects dead routers for later processing

		#check for dead routers
		current_time = int(time.time())
		for n in neighbors:
			if current_time - last_heartbeat[n] > KEEP_ALIVE_THRESHOLD:
					#neighbor has died - too long betwen heartbeats
					dead_neighbors.append(n)
					dead_routers.append(n)
					if DEBUG:
						print "%s's neighbor: router %s died" %(my_id(), n)

		#remove dead routers from dist and dv tables & clean up other node state
		for dead in dead_neighbors:
			stability_delay += STABILITY_DELAY
			dv_changed = collections.defaultdict(list)
			forget_dead_router(dead, neighbors, dv_changed, last_heartbeat, next_hop, most_recent_dvs, my_dist)
			my_dv, next_hop = recompute_dv(my_dist)
			printed_dv = False #allow dv to be printed again

		#notify neighbors every TIME_BETWEEN_ADVERTS seconds
		current_time = int(time.time())
		if current_time - last_advert > TIME_BETWEEN_ADVERTS:
			if stability_delay > 0:
				stability_delay -= 1
			last_advert = current_time
			for n in neighbors:
				msg = find_dv_to_send(my_dv, next_hop, n, link_cost_changed)
				if DEBUG:
					print my_id(), 'sending to %s:' %n
					print msg
				sock.sendto(msg, ('', get_port(neighbors, n)))
			if is_poison() and printed_dv and not link_cost_changed:
				poison_delay -= 1

		printed_dv = print_dv_if_stable(printed_dv, neighbors, dv_changed, stability_delay, my_dv, next_hop)

		#simulate link cost change if poison flag enabled
		if is_poison() and printed_dv and link_cost_changed == False and poison_delay == 0:
			if neighbors != neighbors2:
				neighbors = neighbors2 #apply new link costs after stability detected

				#re-initialise dist table and dv table for this node
				my_dist = initialise_dist(neighbors)
				my_dv = initialise_dv(neighbors)
				if DEBUG:
					print_neighbors(num_neighbors, neighbors)
					print_dist_table(my_dist)
					print_dv_table(my_dv)

			if DEBUG:
				print my_id(), 'has entered poision reverse mode'

			link_cost_changed = True
			dv_changed = collections.defaultdict(list)
			stability_delay += STABILITY_DELAY * 2
			printed_dv = False #allow dv to be printed again

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
	msg = re.sub(": 'inf'", ': -1', msg) #make cost invalid
	dv = eval(msg) #python can't eval float('infinity')

	#remove known dead routers
	filtered_dv = {}
	for router_id in dv:
		if dv[router_id] == -1:
			dv[router_id] = float('infinity') #repair cost as infinite
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

#decides on dv to send the given neighbor
#if poison reverse is not enabled, this is just str(my_dv)
#otherwise, if this node routes thru the given neighbor to get to
#a particular router, the cost to this router is faked as infinite
#this heuristic is applied only after stability is established initially
#and the link cost change has been applied
def find_dv_to_send(my_dv, next_hop, n, link_cost_changed):
	dv_as_str = str(my_dv)
	if not is_poison():
		return dv_as_str
	if not link_cost_changed:
		return dv_as_str
	dv_to_send = copy.deepcopy(my_dv)
	for dest in my_dv:
		dv_to_send[dest] = my_dv[dest]
	for dest in my_dv:
		if next_hop[dest] == n:
			dv_to_send[dest] = 'inf' #py can't eval float('infinity')
	return str(dv_to_send)

#returns True if the dv is stable; False otherwise
def is_dv_stable(neighbors, dv_changed, stability_delay):
	if stability_delay > 0:
		return False
	for n in neighbors:
		if not n in dv_changed:
			return False #don't assume anything until at least one advert
		elif dv_changed[n][len(dv_changed[n])-1]:
			return False #last dv advert changed this nodes' dv
		elif len(dv_changed[n]) > 1 and dv_changed[n][len(dv_changed[n])-2]:
			return False #2nd-last dv advert changed this nodes' dv
	return True

#print dv if dv is considered stable - stability is detected when
#the last two adverts from all nodes have not changed the dv
def print_dv_if_stable(printed_dv, neighbors, dv_changed, stability_delay, my_dv, next_hop):
	if printed_dv == False and is_dv_stable(neighbors, dv_changed, stability_delay):
		printed_dv = True
		print "Router %s's DV table:" %my_id()
		for node in sorted(my_dv):
			print 'shortest path to node %s:' %node,
			print 'the next hop is %s' %next_hop[node],
			print 'and the cost is %.1f' %my_dv[node]
	return printed_dv

#returns a list of all routers in the old dv and not the new dv
#this condition implies that the router has failed
#the reverse is not true - if the dv grows, then new router(s) were discovered
def infer_dead_routers(old_most_recent, received_dv):
	dead_nodes = []
	for node in old_most_recent:
		if not node in received_dv:
			dead_nodes.append(node)
	return dead_nodes

#clears any state associated with a router known to be dead
#the extra checks are necessary in case multiple neighbors suggest a failed node
def forget_dead_router(d, neighbors, dv_changed, last_heartbeat, next_hop, most_recent_dvs, my_dist):
	if d in neighbors: del neighbors[d]
	if d in dv_changed: del dv_changed[d]
	if d in last_heartbeat: del last_heartbeat[d]
	if d in next_hop: del next_hop[d]
	if d in most_recent_dvs: del most_recent_dvs[d]
	if d in my_dist: del my_dist[d]
	for router in my_dist:
		if d in my_dist[router]: del my_dist[router][d]

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
def is_poison():
	if POISON_ON == True:
		return True
	else:
		return False

#kills programs with error message in the event of a bad config file
def bad_input_file(filename):
	print >>sys.stderr, "%s: cannot parse configuration file '%s'" %(sys.argv[0], filename)
	print >>sys.stderr, "%s: perhaps you meant to use the '-p' flag" %sys.argv[0]
	sys.exit(1)

#processes the config file
#returns a dictionary of neighbors in the form (cost, cost', port)
#also returns the number of neighbors
def process_config_file(filename):
	if os.access(filename, os.R_OK) and os.path.isfile(filename):
		lines = open(filename, 'r').readlines()
		neighbors = {}
		new_costs = {}
		first_line = 0
		num_neighbors = 0
		for line in lines:
			if first_line == 0:
				line = line.rstrip('\n')
				num_neighbors = int(line)
				first_line = 1
				continue
			line = line.strip('\n')
			if is_poison():
				try:
					(node_id, cost, new_cost, node_port) = line.split(' ')
				except:
					bad_input_file(filename)
				neighbors[node_id] = (float(cost), int(node_port))
				new_costs[node_id] = (float(new_cost), int(node_port))
			else:
				try:
					(node_id, cost, node_port) = line.split(' ')
				except:
					bad_input_file(filename)
				neighbors[node_id] = (float(cost), int(node_port))
		if not is_poison():
			new_costs = neighbors
		return (neighbors, new_costs, num_neighbors)
	else:
		print >>sys.stderr, "%s: cannot read '%s'" %(sys.argv[0], filename)
		sys.exit(1)

if __name__ == '__main__':

	#require 3 or 4 args
	if len(sys.argv) != 4 and len(sys.argv) != 5:
		args = '<node id> <node port> <config file> [-p]'
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

	#ensure -p or -P is specified as 4th arg
	if len(sys.argv) == 5 and sys.argv[4] != '-p' and sys.argv[4] != '-P':
		print >>sys.stderr, "%s: unrecognised argument '%s', expecting '-p'" %(sys.argv[0], sys.argv[4])
		sys.exit(1)

	NODE_ID = sys.argv[1]
	NODE_PORT = int(sys.argv[2])
	CONFIG_FILE = sys.argv[3]
	POISON_ON = False
	if len(sys.argv) == 5:
		if DEBUG:
			print 'Poison reverse is active'
		POISON_ON = True

	#globals
	TIME_BETWEEN_ADVERTS = 5
	KEEP_ALIVE_THRESHOLD = TIME_BETWEEN_ADVERTS * 3
	STABILITY_DELAY = 2
	POISON_DELAY = 4

	main()
