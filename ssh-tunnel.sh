#! /bin/bash

# if you need to use a key file to connect to the remote server, use the -i flag
i=$1

if [ -z "$i" ]
then

# port forward port 27017 from remote server to localhost port 27069
ssh -L 27069:localhost:27017 -N -f -l ubuntu 54.87.228.164 && echo "tunnel created"
    
fi

if [ -n "$i" ]
then
    echo "using provided key file $i"
    ssh -i $i -L 27069:localhost:27017 -N -f -l ubuntu 54.87.228.164 -i $i -o "IdentitiesOnly=yes"
fi

