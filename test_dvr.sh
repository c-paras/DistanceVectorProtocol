#!/bin/sh
#Written by Costa Paraskevopoulos in May 2017
#Runs the distance vector routing protocol at each node in the given topology

if test $# -ne 1 -a $# -ne 2
then
	echo "Usage: $0 <topology> [-p]" >&2
	exit 1
elif test $# -eq 2 -a "$2" != '-p' -a "$2" != '-P'
then
	echo "$0: expected '-p' as second argument" >&2
	exit 1
else
	topology=$1
	if test -n "$2"
	then
		poison='-p'
	fi
fi

if ! test -d "$topology" || ! test -x "$topology"
then
	echo "$0: cannot access '$topology'" >&2
	exit 1
fi

prog=Dvr.py
if test -n "$poison"
then
	port_num=6000
else
	port_num=2000
fi
initial_port=$port_num

for router in A B C D E F G H I J K L M N O P Q R S T U V W X Y Z
do
	if ! test -e "$topology/config$router.txt"
	then
		continue
	fi
	echo "Running router $router..."
	./$prog $router $port_num "$topology/config$router.txt" $poison &
	port_num=$(($port_num + 1))
	sleep 1
done

if test $port_num -eq $initial_port -a `ps $initial_port | wc -l` -eq 1
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
