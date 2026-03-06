#!/bin/sh
# ./run.sh
export ANSIBLE_HOST_KEY_CHECKING=False
eval "$(ssh-agent -s)"
ssh-add --apple-use-keychain $SSH_PATH
ansible -i hosts.txt all -u ubuntu -m ping
ansible-playbook -i hosts.txt deps.yml
ansible-playbook -i hosts.txt main.yml