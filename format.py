#!/usr/bin/env python3
'''Author: Jeff Peng
   UPI:zpen741
   Student ID:927338164'''
from __future__ import print_function, division
import io
import os
import disktools

INODE_BLOCKS = 16
BLOCK_SIZE = 64
DISK_NAME = 'my-disk'

def high_level_format():
    '''Creates the file system space on disk.
        Warning: calling this erases any existing data in the file system.
    '''
    with open(DISK_NAME, 'r+b') as disk:
        for i in range(INODE_BLOCKS):
            block = bytearray([0] * BLOCK_SIZE)
            disk.write(block)
        disk.flush()

def fill_block(block_number,pattern_number):
    '''use special char to fill a certain block, it always is used as a function to
    delete blocks that used by file.'''
    block = bytearray([pattern_number] * BLOCK_SIZE)
    disktools.write_block(block_number,block)
 
if __name__ == '__main__':
    high_level_format()
    os.system('od --address-radix=x -t x1 -a my-disk')
