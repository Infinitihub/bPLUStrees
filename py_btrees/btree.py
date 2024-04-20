import bisect
from typing import Any, List, Optional, Tuple, Union, Dict, Generic, TypeVar, cast, NewType
from py_btrees.disk import DISK, Address, Disk
from py_btrees.btree_node import BTreeNode, KT, VT, get_node
import math

"""
----------------------- Starter code for your B-Tree -----------------------

Helpful Tips (You will need these):
1. Your tree should be composed of BTreeNode objects, where each node has:
    - the disk block address of its parent node
    - the disk block addresses of its children nodes (if non-leaf)
    - the data items inside (if leaf)
    - a flag indicating whether it is a leaf

------------- THE ONLY DATA STORED IN THE `BTree` OBJECT SHOULD BE THE `M` & `L` VALUES AND THE ADDRESS OF THE ROOT NODE -------------
-------------              THIS IS BECAUSE THE POINT IS TO STORE THE ENTIRE TREE ON DISK AT ALL TIMES                    -------------

2. Create helper methods:
    - get a node's parent with DISK.read(parent_address)
    - get a node's children with DISK.read(child_address)
    - write a node back to disk with DISK.write(self)
    - check the health of your tree (makes debugging a piece of cake)
        - go through the entire tree recursively and check that children point to their parents, etc.
        - now call this method after every insertion in your testing and you will find out where things are going wrong
3. Don't fall for these common bugs:
    - Forgetting to update a node's parent address when its parent splits
        - Remember that when a node splits, some of its children no longer have the same parent
    - Forgetting that the leaf and the root are edge cases
    - FORGETTING TO WRITE BACK TO THE DISK AFTER MODIFYING / CREATING A NODE
    - Forgetting to test odd / even M values
    - Forgetting to update the KEYS of a node who just gained a child
    - Forgetting to redistribute keys or children of a node who just split
    - Nesting nodes inside of each other instead of using disk addresses to reference them
        - This may seem to work but will fail our grader's stress tests
4. USE THE DEBUGGER
5. USE ASSERT STATEMENTS AS MUCH AS POSSIBLE
    - e.g. `assert node.parent != None or node == self.root` <- if this fails, something is very wrong

--------------------------- BEST OF LUCK ---------------------------
"""


# Complete both the find and insert methods to earn full credit
class BTree:
    def __init__(self, M: int, L: int):
        """
        Initialize a new BTree.
        You do not need to edit this method, nor should you.
        """
        self.root_addr: Address = DISK.new()  # Remember, this is the ADDRESS of the root node
        # DO NOT RENAME THE ROOT MEMBER -- LEAVE IT AS self.root_addr
        DISK.write(self.root_addr, BTreeNode(self.root_addr, None, None, True))
        self.M = M  # M will fall in the range 2 to 99999
        self.L = L  # L will fall in the range 1 to 99999

    def insert(self, key: KT, value: VT) -> None:
        """
        Insert the key-value pair into your tree.
        It will probably be useful to have an internal
        _find_node() method that searches for the node
        that should be our parent (or finds the leaf
        if the key is already present).

        Overwrite old values if the key exists in the BTree.

        Make sure to write back all changes to the disk!
        """

        self.insert_helper(key, value, DISK.read(self.root_addr))
        while not self.rule_checker():
            self.rule_fixer()

    def rule_fixer(self):
        self.rule_fixer_helper(DISK.read(self.root_addr))

    def rule_fixer_helper(self, node):
        if len(node.data) > self.L and node.is_leaf:
            if self.root_addr != node.my_addr:
                split = math.ceil(self.L / 2)
                new_data = node.data[split:]
                new_keys = node.keys[split:]
                node.data = node.data[:split]
                node.keys = node.keys[:split]
                new_node = BTreeNode(DISK.new(), node.parent_addr, node.index_in_parent + 1, True)
                new_node.keys = new_keys
                new_node.data = new_data
                parent = node.get_parent()
                parent.is_leaf = False
                parent.children_addrs.insert(new_node.index_in_parent, new_node.my_addr)
                for ind in range(len(parent.children_addrs)):
                    if ind > new_node.index_in_parent:
                        child = DISK.read(parent.children_addrs[ind])
                        child.index_in_parent += 1
                        child.write_back()
                parent.keys.append(max(node.keys))
                parent.keys.sort()
                node.write_back()
                new_node.write_back()
                parent.write_back()
                return
            if self.root_addr == node.my_addr:
                split = math.ceil(self.L / 2)
                new_data = node.data[split:]
                new_keys = node.keys[split:]
                node.data = node.data[:split]
                node.keys = node.keys[:split]
                root = BTreeNode(DISK.new(), None, None, False)
                new_node = BTreeNode(DISK.new(), root.my_addr, 1, True)
                new_node.keys = new_keys
                new_node.data = new_data
                node.index_in_parent = 0
                root.children_addrs.append(node.my_addr)
                node.parent_addr = root.my_addr
                root.children_addrs.insert(new_node.index_in_parent, new_node.my_addr)
                root.keys.append(max(node.keys))
                self.root_addr = root.my_addr
                node.write_back()
                new_node.write_back()
                root.write_back()
                return
        if not node.is_leaf and len(node.keys) > (self.M -1):
            if node.my_addr != self.root_addr:
                split = math.ceil((self.M -1) / 2)
                new_keys = node.keys[split + 1:]
                up_key = node.keys[split]
                node.keys = node.keys[:split]
                new_node = BTreeNode(DISK.new(), node.parent_addr, node.index_in_parent + 1, False)
                if (self.M -1) % 2 == 1:
                    add_split = math.ceil(((self.M -1) + 2) / 2)
                else:
                    add_split = math.ceil(((self.M -1) + 1) / 2)
                new_node.children_addrs = node.children_addrs[add_split:]
                node.children_addrs = node.children_addrs[:add_split]
                for child in new_node.children_addrs:
                    child = DISK.read(child)
                    child.index_in_parent = child.index_in_parent - add_split
                    child.parent_addr = new_node.my_addr
                    child.write_back()
                new_node.keys = new_keys
                parent = node.get_parent()
                parent.is_leaf = False
                parent.children_addrs.insert(new_node.index_in_parent, new_node.my_addr)
                for ind in range(len(parent.children_addrs)):
                    if ind > new_node.index_in_parent:
                        child = DISK.read(parent.children_addrs[ind])
                        child.index_in_parent += 1
                        child.write_back()
                parent.keys.append(up_key)
                parent.keys.sort()
                node.write_back()
                new_node.write_back()
                parent.write_back()
                return
            if node.my_addr == self.root_addr:
                split = math.ceil((self.M -1) / 2)
                new_keys = node.keys[split + 1:]
                up_key = node.keys[split]
                node.keys = node.keys[:split]
                root = BTreeNode(DISK.new(), None, None, False)
                root.children_addrs.append(node.my_addr)
                new_node = BTreeNode(DISK.new(), root.my_addr, 1, False)
                new_node.keys = new_keys
                if (self.M -1) % 2 == 1:
                    add_split = math.ceil(((self.M -1) + 2) / 2)
                else:
                    add_split = math.ceil(((self.M -1)+1)/2)
                new_node.children_addrs = node.children_addrs[add_split:]
                for child in new_node.children_addrs:
                    child = DISK.read(child)
                    child.index_in_parent = child.index_in_parent - add_split
                    child.parent_addr = new_node.my_addr
                    child.write_back()
                node.children_addrs = node.children_addrs[:add_split]
                node.index_in_parent = 0
                node.parent_addr = root.my_addr
                root.children_addrs.insert(new_node.index_in_parent, new_node.my_addr)
                root.keys.append(up_key)
                self.root_addr = root.my_addr
                node.write_back()
                new_node.write_back()
                root.write_back()
                return
        if node.is_leaf:
            return
        if node.children_addrs:
            for child in node.children_addrs:
                self.rule_fixer_helper(DISK.read(child))
        return

    def insert_helper(self, key, value, node):
        node = self.node_to_insert(key, node)
        node.insert_data(key, value)
        node.write_back()

    def node_to_insert(self, key, node):
        index = node.find_idx(key)
        if not node.is_leaf:
            return self.node_to_insert(key, node.get_child(index))
        else:
            return node

    def rule_checker(self):
        return self.rule_checker_help(DISK.read(self.root_addr))

    def rule_checker_help(self, node):
        if node.is_leaf:
            if len(node.data) > self.L or (len(node.data) < math.ceil(self.L / 2) and node.my_addr != self.root_addr):
                return False
            else:
                return True
        if len(node.keys) > (self.M -1) or len(node.children_addrs) > (self.M -1) + 1:
            return False
        if not node.is_leaf:
            for child in node.children_addrs:
                if not self.rule_checker_help(DISK.read(child)):
                    return False
        return True

    def find(self, key: KT) -> Optional[VT]:
        """
        Find a key and return the value associated with it.
        If it is not in the BTree, return None.

        This should be implemented with a logarithmic search
        in the node.keys array, not a linear search. Look at the
        BTreeNode.find_idx() method for an example of using
        the builtin bisect library to search for a number in 
        a sorted array in logarithmic time.
        """
        node = self.node_to_insert(key, DISK.read(self.root_addr))
        if node is not None:
            return node.find_data(key)
        else:
            return None

    def delete(self, key: KT) -> None:
        raise NotImplementedError("Karma method delete()")
