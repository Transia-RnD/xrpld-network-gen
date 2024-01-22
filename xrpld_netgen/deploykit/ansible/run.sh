#!/bin/sh
# ./run.sh
ansible -i hosts.txt all -u ubuntu -m ping
ansible-playbook -i hosts.txt deps.yml
ansible-playbook -i hosts.txt main.yml