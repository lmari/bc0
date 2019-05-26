# bc0

A simple (and still incomplete) blockchain manager, written in python with flask.<br/>
Preconditions: python 3.x with the modules: datetime, flask, flask-wtf, functools, json, requests, socket, wtforms.

Run the server which handles the local host with:

    python bc0.py

or:

    python bc0.py <TCP port>

(for example python bc0.py 5001)

or

    python bc0.py <TCP port> <IP address>

(for example python bc0.py 5001 192.168.0.1)<br />
Then connect the browser to the address.<br />
Each running instance is both a client and a server (i.e., a peer), which can connect to other peers.
