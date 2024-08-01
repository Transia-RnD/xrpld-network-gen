#!/bin/sh
# ./clean.sh
export ANSIBLE_HOST_KEY_CHECKING=False
ansible -i hosts.txt all -u ubuntu -m ping
ansible-playbook -i hosts.txt clean.yml