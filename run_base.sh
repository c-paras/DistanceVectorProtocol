#!/bin/sh
#Written by Costa Paraskevopoulos in May 2017
#Runs the distance vector protocol at each node in the sample topology

prog=Dvr.py
port_num=2000

for router in A B C D E F
do
	echo "Running router $router..."
	./$prog $router $port_num topology1/config$router.txt &
	port_num=$(($port_num + 1))
	sleep 1
done

echo
echo "Press any key to terminate all routers"
while true
do
	read res
	if test -n res
	then
		break
	fi
done
kill `pgrep $prog`
