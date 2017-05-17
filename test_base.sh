#!/bin/sh
#Written by Costa Paraskevopoulos in May 2017
#Runs the distance vector routing protocol at each node in the given topology

if test $# -ne 1
then
	echo "Usage: $0 <topology>" >&2
	exit 1
else
	topology=$1
fi

if ! test -d "$topology" || ! test -x "$topology"
then
	echo "$0: cannot access '$topology'" >&2
	exit 1
fi

prog=Dvr.py
port_num=2000

for router in A B C D E F G H I J K L M N O P Q R S T U V W X Y Z
do
	if ! test -e "$topology/config$router.txt"
	then
		break
	fi
	echo "Running router $router..."
	./$prog $router $port_num "$topology/config$router.txt" &
	port_num=$(($port_num + 1))
	sleep 1
done

if test $port_num -eq 2000 -a `ps 2000 | wc -l` -eq 1
then
	echo "$0: no configuration files in '$topology'" >&2
	exit 1
fi

echo
echo "Press ENTER to terminate all routers"
echo
while true
do
	read res
	if test -n res
	then
		break
	fi
done
kill `pgrep $prog` 2> /dev/null
