"""
This file is part of BC0, Copyright 2018, Luca Mari.

BC0 is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 2.

BC0 is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
See the GNU General Public License <http://www.gnu.org/licenses/> for more details.
"""
import sys
import os.path
from functools import wraps
import socket
from flask import Flask, request, session, render_template
from flask_wtf import FlaskForm
from wtforms import StringField
import requests
import json
import datetime as date
import bc0lib as bc

IPAddr = socket.gethostbyname(socket.gethostname())

myport = 5000 if len(sys.argv) == 1 else int(sys.argv[1])
myhost = IPAddr if len(sys.argv) <= 2 else sys.argv[2]
hostid = myhost + ':' + str(myport)
x = 'bc0.html'  # flask html template

if getattr( sys, 'frozen', False ):     # running in a bundle
    app_folder = os.path.dirname(sys.executable)
    template_folder = sys._MEIPASS
    print('*** Running in a bundle: ' + app_folder + ' -- ' + template_folder)
else:   # running live
    app_folder = '.'
    template_folder = '.'
    print('*** Running live: ' + app_folder + ' -- ' + template_folder)
print('*** from host: ' + IPAddr)

app = Flask(__name__, template_folder=template_folder)
app.config['SECRET_KEY'] = 'abcabcabc'


class IdForm(FlaskForm):
    id = StringField('id')


class WorkForm(FlaskForm):
    name = StringField('name')
    host = StringField('host')
    data = StringField('data')


# Helper (local) functions **************************************
def not_given(name):
    return name is None or len(name) == 0

def h_read_file(filename, jsoned=False):
    """Read a (local) file."""
    if not_given(filename):
        res = {'code': '-1'}      # ko: missing filename
        return res if not jsoned else json.dumps(res)
    try:
        with open(filename, 'r') as fin:
            data = fin.read()
            res = {'code': '0', 'data': data}   # ok
            return res if not jsoned else json.dumps(res)
    except:
        res = {'code': '-2'}      # ko: problems in reading the file
        return res if not jsoned else json.dumps(res)

def h_write_file(filename, data):
    """Write a (local) file."""
    if not_given(filename): return "-1"       # ko: missing filename
    try:
        with open(filename, 'w') as fout:
            print(data, file=fout)
        return '0'      # ok
    except:
        return '-2'     # ko:  problems in writing the file

def h_delete_file(filename):
    """Delete a (local) file."""
    if not_given(filename): return "-1"       # ko: missing filename
    try:
        os.remove(filename)
        return "0"      # ok
    except:
        return '-2'     # ko:  problems in deleting the file

def adapt_to_win(bc_host):
    return bc_host.replace(":", "_")

def get_host_list(bc_name, bc_host):
    """Get the list of hosts maintaining this blockchain."""
    filename = app_folder + '/' + bc_name + '_' + adapt_to_win(bc_host) + '_hosts'
    if not os.path.isfile(filename):
        return {'code': '-1'}      # ko: missing filename
    try:
        with open(filename, 'r') as fin:
            data = fin.read()
            data = json.loads(data)
            data = data['hosts']
        return {'code': '0', 'data': data}     # ok
    except:
        return {'code': '-2'}      # ko: problems in getting the file

def not_logged_in():
    return 'userid' not in session

def t_no_user():
    return render_template(x, hostid=hostid, msg='No user logged in.')

def t_missing_name(msg):
    return render_template(x, hostid=hostid, userid=session['userid'], msg=msg)

def t_bad_file(res, filename, bcname):
    if res['code'] == '-1': return render_template(x, hostid=hostid, userid=session['userid'], bcname=bcname, msg="Error in reading the blockchain file '" + filename + "'.")
    if res['code'] == '-2': return render_template(x, hostid=hostid, userid=session['userid'], bcname=bcname, msg="Problems in getting data from the blockchain file '" + filename + "'.")

def t_bad_list(res, filename, bcname):
    if res['code'] == '-1': return render_template(x, hostid=hostid, userid=session['userid'], bcname=bcname, msg="The blockchain '" + bcname + "' does not exist.")
    if res['code'] == '-2': return render_template(x, hostid=hostid, userid=session['userid'], bcname=bcname, msg="Problems in getting data from the blockchain file '" + filename + "'.")

def t_default(bcname='', bchost='', msg=''):
    return render_template(x, hostid=hostid, userid=session['userid'], bcname=bcname, bchost=bchost, msg=msg)

def read_form(with_host=False, with_data=False):
    WorkForm(request.form)
    bc_name = request.form['name']
    if with_host: return bc_name, request.form['host']
    if with_data: return bc_name, request.form['data']
    return bc_name

def send_http_req(host, req, data):
    headers = {'content-type': 'application/json'}
    url = 'http://' + host + req
    print('Sending an update request to ' + host + '...')
    req = requests.post(url, data=json.dumps(data), headers=headers, timeout=1.0)
    req.raise_for_status()

def send_http_req_to_all_hosts(bc_name, bc_host, host_list, act_name, act_desc, data):
    if host_list == '':
        res = get_host_list(bc_name, bc_host)
        if res['code'] != '0': return t_bad_list(res, app_folder + '/' + bc_name + '_' + bc_host + '_hosts', bc_name)
        host_list = res['data']
        if len(host_list) == 1: return t_default(bcname=bc_name, msg="The blockchain '" + bc_name + "' has been " + act_desc + " locally.")
        ###render_template(x, userid=session['userid'], bcname=bc_name, msg="The blockchain '" + bc_name + "' has been " + act_desc + " locally.")
    s = ''
    for h in host_list:
        if h != request.host:
            try:
                send_http_req(h, act_name, data)
            except:
                s += h + ' '
    msg = ', but there has been problems with the hosts ' + s + ')' if len(s) > 0 else ' and in all remote hosts'
    return t_default(bcname=bc_name, msg="The blockchain '" + bc_name + "' has been " + act_desc + " locally" + msg + ".")
    ###render_template(x, userid=session['userid'], bcname=bc_name, msg="The blockchain '" + bc_name + "' has been " + act_desc + " locally" + msg + ".")


# Helper (web remote) functions **********************************
@app.route('/get_chain_hosts', methods=['GET'])
def get_chain_hosts():
    """Get the list of hosts of the specified blockchain from the specified host."""
    bc_name = request.args.get('name')
    bc_host = request.host
    filename = app_folder + '/' + bc_name + '_' + adapt_to_win(bc_host) + '_hosts'
    res = h_read_file(filename)
    if res['code'] != '0': return t_bad_file(res, filename, bc_name)
    return res['data']


@app.route('/set_chain_hosts', methods=['POST'])
def set_chain_hosts():
    data_dict = json.loads(request.data)
    bc_name = data_dict['name']
    host_list = data_dict['hosts']
    filename = app_folder + "/" + bc_name + "_" + adapt_to_win(request.host) + "_hosts"
    data = {"hosts": host_list}
    return h_write_file(filename, json.dumps(data))


@app.route('/upgrade_chain', methods=['POST'])
def upgrade_chain():
    data_dict = json.loads(request.data)
    bc_name = data_dict['name']
    data = data_dict['data']
    filename = app_folder + "/" + bc_name + "_" + adapt_to_win(request.host) + "_chain"
    return h_write_file(filename, data)


@app.route('/get_remote_chain', methods=['GET'])
def get_remote_chain():
    filename = request.args.get('filename')
    return h_read_file(filename, jsoned=True)


@app.route('/delete_remote_chain', methods=['POST'])
def delete_remote_chain():
    data_dict = json.loads(request.data)
    bc_name = data_dict['name']
    filename1 = app_folder + '/' + bc_name + '_' + adapt_to_win(request.host) + '_hosts'
    filename2 = app_folder + '/' + bc_name + '_' + adapt_to_win(request.host) + '_chain'
    res1 = h_delete_file(filename1)
    res2 = h_delete_file(filename2)
    if res1 != "0" or res2 != "0": return "-1"
    return "0"


# Decorator ******************************************************
def check_call(the_function):

    @wraps(the_function)
    def the_wrapper():
        if not_logged_in(): return t_no_user()
        bc_name = read_form()
        if not_given(bc_name): return t_missing_name('Please specify a name for the blockchain.')
        return the_function()

    return the_wrapper


# Basic (web local) functions ************************************
@app.route("/", methods=['GET', 'POST'])
def home():
    return render_template(x, hostid=hostid)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET': return render_template(x)
    userid = request.form['userid']
    if not_given(userid): return render_template(x, msg='Please specify a userid.')
    if 'userid' in session: return render_template(x, userid=userid, msg="User '" + session['userid'] + "' is already logged in.")
    session['userid'] = userid
    return render_template(x, hostid=hostid, userid=userid, msg=session['userid'] + ' logged in.')


@app.route("/logout")
def logout():
    if not_logged_in(): return t_no_user()
    userid = session['userid']
    session.pop('userid', None)
    return render_template(x, hostid=hostid, msg=userid + ' logged out.')


@app.route('/create_chain', methods=['POST'])
@check_call
def create_chain():
    bc_name = read_form()
    filename1 = app_folder + '/' + bc_name + '_' + adapt_to_win(request.host) + '_hosts'
    filename2 = app_folder + '/' + bc_name + '_' + adapt_to_win(request.host) + '_chain'
    if os.path.isfile(filename1): return t_default(bcname=bc_name, msg="A blockchain named '" + bc_name + "' already exists.")
    # Create the two required local files
    chain = bc.Blockchain(name=bc_name, author=session['userid'])
    hosts_data = {"hosts": [request.host]}
    res1 = h_write_file(filename1, json.dumps(hosts_data))
    res2 = h_write_file(filename2, chain.write_me(jsoned=True))
    if res1 != "0" or res2 != "0": return t_default(bcname=bc_name, msg="Problems in creating the blockchain file '" + filename1 + "'.")
    return t_default(bcname=bc_name, msg="The blockchain '" + bc_name + "' has been created.")


@app.route('/delete_chain', methods=['POST'])
@check_call
def delete_chain():     # ***bisogna cancellare la bc da tutti gli host
    bc_name = read_form()
    # Read the local chain hosts
    res = get_host_list(bc_name, request.host)
    if res['code'] != '0': return t_bad_list(res, app_folder + '/' + bc_name + '_' + request.host + '_hosts', bc_name)
    host_list = res['data']
    # Delete the chain locally
    filename1 = app_folder + '/' + bc_name + '_' + adapt_to_win(request.host) + '_hosts'
    filename2 = app_folder + '/' + bc_name + '_' + adapt_to_win(request.host) + '_chain'
    res1 = h_delete_file(filename1)
    res2 = h_delete_file(filename2)
    if res1 != "0" or res2 != "0": return t_default(bcname=bc_name, msg="Problems in deleting the blockchain '" + bc_name + "'.")
    # Upgrade hosts
    return send_http_req_to_all_hosts(bc_name, request.host, host_list, '/delete_remote_chain', 'deleted', {'name': bc_name})


@app.route('/list_chain_hosts', methods=['POST'])
@check_call
def list_chain_hosts():
    bc_name = read_form()
    # Get the list of hosts
    res = get_host_list(bc_name, request.host)
    if res['code'] != '0': return t_bad_list(res, app_folder + '/' + bc_name + '_' + request.host + '_hosts', bc_name)
    return t_default(bcname=bc_name, msg=res['data'])


@app.route('/show_content', methods=['POST'])
@check_call
def show_content():
    bc_name = read_form()
    # Read the chain and show its content
    filename = app_folder + '/' + bc_name + '_' + adapt_to_win(request.host) + '_chain'
    res = h_read_file(filename)
    if res['code'] != '0': return t_bad_file(res, filename, bc_name)
    return t_default(bcname=bc_name, msg=res['data'])


@app.route('/check_chain', methods=['POST'])
@check_call
def check_chain():
    bc_name = read_form()
    # Read the chain and check it
    filename = app_folder + '/' + bc_name + '_' + adapt_to_win(request.host) + '_chain'
    res = h_read_file(filename)
    if res['code'] != '0': return t_bad_file(res, filename, bc_name)
    chain = bc.load_blockchain(res['data'])
    check = chain.check_me()
    if check == -1: return t_default(bcname=bc_name, msg="The blockchain '" + bc_name + "' is ok!")
    return t_default(bcname=bc_name, msg="The blockchain '" + bc_name + "' is in a wrong state from block " + str(check) + "!")


@app.route('/enter_chain', methods=['POST'])
@check_call
def enter_chain():
    bc_name, bc_host = read_form(with_host=True)
    if not_given(bc_host): return t_default(bcname=bc_name, msg='Please specify the host of the blockchain to enter.')
    if bc_host == request.host: return render_template(x, userid=session['userid'], bcname=bc_name, bchost=bc_host, msg='The host of the blockchain to enter must not be the current host.')
    # Get the host list from the specified remote host
    try:
        res = requests.get('http://' + bc_host + '/get_chain_hosts?name=' + bc_name, timeout=1)
        res.raise_for_status()
        data = res.text
    except:
        return t_default(bcname=bc_name, bchost=bc_host, msg='Unable to complete the request to ' + bc_host + '.')
    # Upgrade the host list
    try:
        parsed_data = json.loads(data)
        host_list = parsed_data['hosts']
        for h in host_list:
            if h == request.host:
                return t_default(bcname=bc_name, bchost=bc_host, msg='This address is already in the list of the blockchain hosts.')
    except:
        return t_default(bcname=bc_name, bchost=bc_host, msg='Unable to parse the data about the hosts of the blockchain.')
    host_list.append(request.host)
    data = {"hosts": host_list}
    res = h_write_file(app_folder + '/' + bc_name + '_' + adapt_to_win(request.host) + '_hosts', json.dumps(data))
    if res != '0': return t_default(bcname=bc_name, bchost=bc_host, msg="Problems in upgrading the blockchain '" + bc_name + "'.")
    # Get the chain data from the specified remote host
    try:
        res = requests.get('http://' + bc_host + '/get_remote_chain?filename=' + bc_name + '_' + adapt_to_win(bc_host) + '_chain', timeout=0.1)
        res.raise_for_status()
        data = res.text.replace("'", "\"")  # json requires property names delimited by double quotes...
        parsed_data = json.loads(data)
        if parsed_data['code'] != '0':
            return t_default(bcname=bc_name, bchost=bc_host, msg='The download of the blockchain data has not been completed.')
        else:
            h_write_file(app_folder + '/' + bc_name + '_' + adapt_to_win(request.host) + '_chain', parsed_data['data'])
    except:
        return t_default(bcname=bc_name, bchost=bc_host, msg='The download of the blockchain data has not been completed.')
    # Upgrade hosts
    return send_http_req_to_all_hosts(bc_name, request.host, host_list, '/set_chain_hosts', 'upgraded', {'name': bc_name, 'hosts': host_list})


@app.route('/leave_chain', methods=['POST'])
@check_call
def leave_chain():
    bc_name = read_form()
    # Read the local chain hosts
    res = get_host_list(bc_name, request.host)
    if res['code'] != '0': return t_bad_list(res, app_folder + '/' + bc_name + '_' + request.host + '_hosts', bc_name)
    host_list = res['data']
    # Upgrade data locally
    for h in host_list:
        if h == request.host: host_list.remove(h)
    res1 = h_delete_file(app_folder + '/' + bc_name + '_' + adapt_to_win(request.host) + '_hosts')
    res2 = h_delete_file(app_folder + '/' + bc_name + '_' + adapt_to_win(request.host) + '_chain')
    if res1 != "0" or res2 != "0": return t_default(bcname=bc_name, msg="Problems in leaving the blockchain '" + bc_name + "'.")
    if len(host_list) == 0: return t_default(bcname=bc_name, msg="The blockchain '" + bc_name + "' has been left locally and deleted.")
    # Upgrade hosts
    return send_http_req_to_all_hosts(bc_name, request.host, host_list, '/set_chain_hosts', 'upgraded', {'name': bc_name, 'hosts': host_list})


@app.route('/add_data', methods=['POST'])
@check_call
def add_data():
    bc_name, bc_data = read_form(with_data=True)
    if not_given(bc_data): return t_default(bcname=bc_name, msg='Please specify the data to add to the blockchain.')
    # Remove quotes in data (not so nice solution...)
    bc_data = bc_data.replace("'", " ").replace('"', ' ')
    # Read the local chain
    filename = app_folder + '/' + bc_name + '_' + adapt_to_win(request.host) + '_chain'
    res = h_read_file(filename)
    if res['code'] != '0': return t_bad_file(res, filename, bc_name)
    chain = bc.load_blockchain(res['data'])
    # Add data locally
    chain.add_data(session['userid'], bc_data)
    chain.add_block(date.datetime.now())
    data = chain.write_me(jsoned=True)
    res = h_write_file(filename, data)
    if res != "0": return t_default(bcname=bc_name, msg="Problems in updating the blockchain file '" + filename + "'.")
    # Upgrade hosts
    return send_http_req_to_all_hosts(bc_name, request.host, '', '/upgrade_chain', 'upgraded', {'name': bc_name, 'data': data})


app.run(port=myport, host=myhost)
