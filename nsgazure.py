#!/usr/bin/env python
import os
import argparse as ap
import sys
import json
import subprocess as s
import mysql.connector as mysqlcon

# MySQL connector
con = mysqlcon.connect(user='root', password=os.environ.get("mysqlroot"), host='127.0.0.1', database='nsgstore')
cur = con.cursor()

# Azure cli location
azurecli = ["/usr/local/bin/azure"]

# Defining the arguments needed to trigger NSG changes
# Default arguments needed to trigger the data dump
parser = ap.ArgumentParser()
parser.add_argument("network", nargs='?')
parser.add_argument("nsg", nargs='?')
parser.add_argument("rule", nargs='?')
parser.add_argument('action', nargs='?')
parser.add_argument('--resource-group', action="store", dest="resource_group")
parser.add_argument('--nsg-name', action="store", dest="nsg_name")
parser.add_argument('--subscription', action="store", dest="subscription")
args, unknown = parser.parse_known_args()

# Print statements to check arg values
print args.network
print args.nsg
print args.rule
print args.action

valid_actions = ("create", "set", "delete")

# If line arguments do not contain the following args then wrapper will pass the commands to the original cli
if not args.network == "network" and not args.nsg == "nsg" and not args.rule == "rule" and not args.action == valid_actions:
    if len(sys.argv) > 1:
        azurecli = azurecli + sys.argv[1:]
    s.call(azurecli)
    sys.exit()

# Save the command inputs as a string
savecommand = azurecli + sys.argv[1:]
command_string =  " ".join(savecommand)

# Collecting account info and retrieving user account logged in
proc = s.Popen([azurecli[0], "account", "show", "--json"], stdout=s.PIPE)
account_output = proc.communicate()[0]
account = json.loads(account_output)[0]
account_name = account["user"]["name"]
print account_name

# Function to collect NSG json dumps
def jsondump():
    proc = s.Popen([azurecli[0], 
                                "network", 
                                "nsg", 
                                "show", 
                                "--resource-group", 
                                args.resource_group, 
                                "--name", 
                                args.nsg_name, 
                                "--subscription", 
                                args.subscription, 
                                "--json"], 
                                stdout=s.PIPE)
    x = proc.communicate()[0]
    if x == "{}\n":
        print "ERROR: Incorrect parameters"
    return x

pre = jsondump()

#print pre

# Insert query to dump into mysql
pre_run = ("INSERT INTO mytable "
                    "(User_account, Pre_or_Post, State, Subscription, Resource_Group, NSG_Name, Command) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s)")
pre_insert = (account_name, 'pre_run', pre.rstrip(), args.subscription, args.resource_group, args.nsg_name, command_string)

# Insert pre data
cur.execute(pre_run, pre_insert)
con.commit()

# If delete command, append quiet option to remove prompt
if args.action == "delete":
    s.call(azurecli + sys.argv[1:] + ["--quiet"])
else:
    s.call(azurecli + sys.argv[1:])

# Capture json dump post command and insert
post = jsondump()
post_run = ("INSERT INTO mytable "
                    "(User_account, Pre_or_Post, State, Subscription, Resource_Group, NSG_Name, Command) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s)")
post_insert = (account_name, 'post_run', post.rstrip(), args.subscription, args.resource_group, args.nsg_name, command_string)#

cur.execute(post_run, post_insert)
con.commit()

con.close()
