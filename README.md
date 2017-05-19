# DistanceVectorProtocol
Implements the distance vector routing protocol over UDP

This application was built and tested on Ubuntu 64-bit 16.04 LTS using Python version 2.7.12.

* An instance of a routing protocol can be launched by running
```
./Dvr.py <node id> <node port> <config file> [-p]
```
where `node id` is a single uppercase letter, `node port` is greater than 1023 and `config file` is a file describing the local topology of the node. If the `-p` flag is specified, then poisoned reverse is enabled; otherwise, it is disabled.
* A valid `config file` has the following format:
	* The first line indicates the number of neighbors the node has
	* Each line after that describes a particular neighbor, consisting of:
		* The `node id` of that neighbor
		* The cost to reach that neighbor
		* The `node port` of that neighbor
* Several topologies are provided in the directories `topology1`, `topology2` etc. Each topology contains a file in the above format for each node.
* To test basic distance vector routing, run
```
./test_base.sh <topology>
```
where `topology` is the name of one of the topology directories. Once the distance vector (DV) tables stabilize, each node will display their DV table.
* To test the handling of node failure(s):
	* Wait for the DV tables to stabilize and display
	* Find the process ID of the node instances by running `pgrep Dvr.py`
	* Choose a node that when failed, will not partition the network and find it's process ID using `ps <pid>`
	* Kill the process running that node's routing protocol using `kill <pid>`
	* Wait for the DV tables to stabilize
	* Repeat for more node failures

Copyright (C) 2017 Costa Paraskevopoulos

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see http://www.gnu.org/licenses/.
