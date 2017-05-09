#!/usr/bin/python
#Written by Costa Paraskevopoulos in May 2017
#Implements the distance vector routing protocol over UDP

import sys, re, os, time, select
from socket import *

DEBUG = 1

def main():
	neighbors, num_neighbors = process_config_file(CONFIG_FILE)
	if DEBUG:
		print num_neighbors
		for n in neighbors:
			print n, get_cost(neighbors, n), get_port(neighbors, n)

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
			neighbors[node_id] = (cost, node_port)
		return (neighbors, num_neighbors)
	else:
		print >>sys.stderr, sys.argv[0] + ': cannot read', filename
		sys.exit(1)

#getters
def get_cost(neighbors, node_id):
	return neighbors[node_id][0]
def get_port(neighbors, node_id):
	return neighbors[node_id][1]
def my_id():
	return NODE_ID
def my_port():
	return NODE_PORT

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
