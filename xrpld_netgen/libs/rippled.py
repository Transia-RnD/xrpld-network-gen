#!/usr/bin/env python
# coding: utf-8

import re
import os
import json
from datetime import datetime
from typing import Dict, Any, List  # noqa: F401

from xrpld_netgen.utils.misc import read_json
import hashlib

basedir = os.path.abspath(os.path.dirname(__file__))
parentdir = os.path.dirname(basedir)

def parse(value: str):
    if value == "no":
        return False
    else:
        return True


def get_feature_lines_from_path(path: str):
    with open(path, "r") as f:
        lines = f.readlines()
        return lines


def get_feature_lines_from_content(content: str):
    return content.decode('utf-8').splitlines()


def parse_rippled_amendments(lines: Any):
    amendments = {}
    for line in lines:
        if re.match(r"REGISTER_FEATURE", line) or re.match(r"REGISTER_FIX", line):
            amendment_name: str = ""
            if re.match(r"REGISTER_FIX", line):
                amendment_name = (
                    re.search("REGISTER_FIX\)?.*?\((.*?),", line).group(1) or 0
                )
            if re.match(r"REGISTER_FEATURE", line):
                amendment_name = (
                    re.search("REGISTER_FEATURE\((.*?),", line).group(1) or 0
                )
            supported = re.findall(r"Supported::(.*),", line)
            default_vote = re.findall(r"DefaultVote::(.*),", line)
            amendments[amendment_name] = {
                "supported": parse(supported[0] if supported else "no"),
                "default_vote": parse(default_vote[0] if default_vote else "no"),
            }
    return {
        k: hashlib.sha512(k.encode("utf-8")).digest().hex().upper()[:64]
        for (k, v) in amendments.items()
        if v["supported"] == True
    }


def convert_to_list_of_hashes(features):
    return list(features.values())


def update_amendments(features: Dict[str, Any], xrpl_protocol: str):
    # load the json string into a dictionary
    json_dict = read_json(f'{parentdir}/genesis.{xrpl_protocol}.json')

    new_amendments: List[str] = convert_to_list_of_hashes(features)

    # loop through the list of dictionaries in accountState
    for dct in json_dict['ledger']['accountState']:
        # check if the dictionary has a key called 'Amendments'
        if 'Amendments' in dct:
            # if it does, update it's value with the new amendments
            dct['Amendments'] = new_amendments

    return json_dict
