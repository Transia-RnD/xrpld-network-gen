#!/bin/sh
# ./clean.sh
ansible -i hosts.txt all -u ubuntu -m ping
ansible-playbook -i hosts.txt clean.yml