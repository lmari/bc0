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

# Blockchain with blocks with multiple JSON-structured data entries
import hashlib as hasher
import datetime as date
import json


class DataItem:
    """Handle a data item, the minimum chunk of information that can be added
    to a block of a blockchain."""

    def __init__(self, index, timestamp, author, data):
        """Class constructor: create a data item."""
        self.index = index
        self.timestamp = str(timestamp)
        self.author = author
        self.data = data

    def dump_me(self):
        """Get this data item as a dictionary."""
        return {
            "ts": self.timestamp,
            "au": self.author,
            "da": self.data
        }

    def write_me(self, jsoned=False, indented=False):
        """Get this data item as a wrapped dictionary or a json string."""
        dic = {self.index: self.dump_me()}
        if not jsoned:
            return dic
        return json.dumps(dic, indent=2) if indented else json.dumps(dic)


class Block:
    """Handle a block as the atomic component of a blockchain."""

    def __init__(self, index, timestamp, data, previous_hash):
        """Class constructor: create and hash a block."""
        self.index = index
        self.timestamp = str(timestamp)
        self.data = data
        self.previous_hash = previous_hash

    def hash_me(self):
        """Generate the hash of this block."""
        sha = hasher.sha256()
        to_hash = str(self.dump_me()).encode('utf-8')
        sha.update(to_hash)
        return sha.hexdigest()

    def get_num_data_items(self):
        """Get the number of data items in this block."""
        return len(self.data)

    def get_data_item(self, num):
        """Get the specified data item of this chain."""
        return self.data[num] if num < self.get_num_data_items() else None

    def dump_me(self):
        """Get this block as a dictionary."""
        item_data_dic = {i: self.get_data_item(i).dump_me() for i in range(self.get_num_data_items())}
        return {
            "ts": self.timestamp,
            "ph": self.previous_hash,
            "da": item_data_dic
        }

    def write_me(self, jsoned=False, indented=False):
        """Get this block as a wrapped dictionary or a json string."""
        dic = {self.index: self.dump_me()}
        if not jsoned:
            return dic
        return json.dumps(dic, indent=2) if indented else json.dumps(dic)


class Blockchain:
    """Handle a blockchain."""

    def __init__(self, name="default name", author="author of genesis block", data="genesis block"):
        """Class constructor: create and init a blockchain."""
        self.name = name
        index = 0
        timestamp = date.datetime.now()
        previous_hash = "0"
        data_item = DataItem(index, timestamp, author, data)
        data = {index: data_item}
        block = Block(index, timestamp, data, previous_hash)
        self.chain = {index: block}
        self.current_data = {}

    def get_num_blocks(self):
        """Get the number of blocks in this blockchain."""
        return len(self.chain)

    def get_block(self, num):
        """Get the specified block of this blockchain."""
        return self.chain[num] if num < self.get_num_blocks() else None

    def add_data(self, author, data):
        """Add the specified data to the queue of this blockchain."""
        index = len(self.current_data)
        data_item = DataItem(index, date.datetime.now(), author, data)
        self.current_data.update({index: data_item})
        return data_item

    def add_block(self, timestamp):
        """Generate a block and add it to this blockchain."""
        index = self.get_num_blocks()
        previous_hash = self.get_block(index - 1).hash_me()
        block = Block(index, timestamp, self.current_data, previous_hash)
        self.chain.update({index: block})
        self.current_data = {}
        return block
    
    def add_existing_block(self, block):
        """Add an existing block to this blockchain."""
        index = self.get_num_blocks()
        self.chain.update({index: block})
        return block

    def check_me(self):
        """Check the integrity of this blockchain;
        Return -1 if the chain is ok or the index of the first corrupted block."""
        for i in range(self.get_num_blocks() - 1):
            if self.get_block(i).hash_me() != self.get_block(i + 1).previous_hash:  # check across blocks
                return i
        return -1

    def dump_me(self):
        """Get this blockchain as a dictionary."""
        block_dic = {i: self.get_block(i).dump_me() for i in range(self.get_num_blocks())}
        return block_dic

    def write_me(self, jsoned=False, indented=False):
        """Get this blockchain as a wrapped dictionary or a json string."""
        dic = {self.name: self.dump_me()}
        if not jsoned:
            return dic
        return json.dumps(dic, indent=2) if indented else json.dumps(dic)


def load_block(desc):
    desc = json.loads(desc)
    i = list(desc.keys())[0]
    di = desc[i]
    block = Block(i, di["ts"], {}, di["ph"])
    num_data_items = len(di["da"])
    for j in range(num_data_items):
        dij = di["da"][str(j)]
        data_itemj = DataItem(j, dij["ts"], dij["au"], dij["da"])
        block.data.update({j: data_itemj})
    return block


def load_blockchain(desc, only_genesis=False):
    """Create a blockchain from a jsoned string."""
    desc = json.loads(desc)
    name = list(desc.keys())[0]
    num_blocks = len(desc[name])
    b0 = desc[name]["0"]
    b0data_item0 = b0["da"]["0"]
    blockchain = Blockchain(name, b0data_item0["au"], b0data_item0["da"])
    block0 = blockchain.get_block(0)
    block0.timestamp = b0["ts"]
    block0.previous_hash = b0["ph"]
    block0.get_data_item(0).timestamp = b0["ts"]
    if only_genesis:
        return blockchain
    for i in range(1, num_blocks):
        bi = desc[name][str(i)]
        blocki = Block(i, bi["ts"], {}, bi["ph"])
        num_data_items = len(bi["da"])
        for j in range(num_data_items):
            dij = bi["da"][str(j)]
            data_itemj = DataItem(j, dij["ts"], dij["au"], dij["da"])
            blocki.data.update({j: data_itemj})
        blockchain.chain.update({i: blocki})
    return blockchain
