#!/usr/bin/env python3
'''Author: Jeff Peng
   UPI:zpen741
   Student ID:927338164'''
from __future__ import print_function, absolute_import, division

import logging
import disktools
import struct
import os
import format

from collections import defaultdict
from errno import ENOENT
from stat import S_IFDIR, S_IFLNK, S_IFREG
from time import time

from fuse import FUSE, FuseOSError, Operations, LoggingMixIn

INODE_BLOCKS = 16
BLOCK_SIZE = 64
DISK_NAME = 'my-disk'

if not hasattr(__builtins__, 'bytes'):
    bytes = str

def bytesToFloat(h1,h2,h3,h4):
    ba = bytearray()
    ba.append(h1)
    ba.append(h2)
    ba.append(h3)
    ba.append(h4)
    return struct.unpack("!f",ba)[0]
    
def floatToBytes(f):
    bs = struct.pack("f",f)
    return (bs[3],bs[2],bs[1],bs[0])
    
def write_not_available_sign(location):
    saved_info_block=disktools.read_block(0)
    saved_info_block[location]=1
    disktools.write_block(0,saved_info_block)
    
def get_available_block_number(type,temp_used=0):
    available_block=disktools.read_block(0)
    if type==0:
        for i in range(0,8):
            if available_block[i]==0:
                return i
    if type==1:
        for i in range(8,16):
            if available_block[i]==0 and i!=temp_used:
                return i
    return 0

class Memory(LoggingMixIn, Operations):
    'Example memory filesystem. Supports only one level of files.'

    def __init__(self):
        self.files = {}
        self.data = defaultdict(bytes)
        self.fd = 0
        now = time()
        self.files['/'] = dict(
            st_mode=(S_IFDIR | 0o755),
            st_ctime=now,
            st_mtime=now,
            st_atime=now,
            st_nlink=2,
            st_uid=os.getuid(),
            st_gid=os.getgid(),
            st_inode=1)
            
        inode_block = bytearray([0] * BLOCK_SIZE)
        #available_sign_block = bytearray([0] * BLOCK_SIZE)
        inode_block[0:2]=disktools.int_to_bytes(self.files['/']['st_mode'],2)
        inode_block[2:4]=disktools.int_to_bytes(self.files['/']['st_uid'],2)
        inode_block[4:6]=disktools.int_to_bytes(self.files['/']['st_gid'],2)
        inode_block[6]=self.files['/']['st_nlink']
        inode_block[7:9]=disktools.int_to_bytes(0,2)
        inode_block[9:13]=floatToBytes(self.files['/']['st_ctime'])
        inode_block[13:17]=floatToBytes(self.files['/']['st_mtime'])
        inode_block[17:21]=floatToBytes(self.files['/']['st_atime'])
        #inode_block[19:27]=b'0x9'
        inode_block[21]=0   #location 1
        inode_block[22]=0   #location 2
        str='/'
        inode_block[23:39]=str.encode('utf-8')
        inode_block[39]=self.files['/']['st_inode']
        disktools.write_block(1,inode_block)
        write_not_available_sign(0)
        write_not_available_sign(1)
        #os.system('od --address-radix=x -t x1 -a my-disk')
        
        #print(inode_block)
    def chmod(self, path, mode):
        self.files[path]['st_mode'] &= 0o770000
        self.files[path]['st_mode'] |= mode
        return 0

    def chown(self, path, uid, gid):
        self.files[path]['st_uid'] = uid
        self.files[path]['st_gid'] = gid

    def create(self, path, mode):
        self.files[path] = dict(
            st_mode=(S_IFREG | mode),
            st_nlink=1,
            st_size=0,
            st_ctime=time(),
            st_mtime=time(),
            st_atime=time(),
            st_uid=os.getuid(),
            st_gid=os.getgid(),
            st_location0=0,
            st_location1=0)

        inode_block = bytearray([0] * BLOCK_SIZE)
        #available_sign_block = bytearray([0] * BLOCK_SIZE)
        inode_block[0:2]=disktools.int_to_bytes(self.files[path]['st_mode'],2)
        inode_block[2:4]=disktools.int_to_bytes(self.files[path]['st_uid'],2)
        inode_block[4:6]=disktools.int_to_bytes(self.files[path]['st_gid'],2)
        inode_block[6]=self.files[path]['st_nlink']
        inode_block[7:9]=disktools.int_to_bytes(self.files[path]['st_size'],2)
        inode_block[9:13]=floatToBytes(self.files[path]['st_ctime'])
        inode_block[13:17]=floatToBytes(self.files[path]['st_mtime'])
        inode_block[17:21]=floatToBytes(self.files[path]['st_atime'])
        inode_block[21]=self.files[path]['st_location0']
        inode_block[22]=self.files[path]['st_location1']
        str=path
        inode_block[23:39]=str.encode('utf-8')
        available_inode_num=get_available_block_number(0)
        if available_inode_num==0:
            logging.info("There is not any available inode block!")
            raise IOError("There is not any available inode block!")
        else:
            self.files[path]['st_inode']=available_inode_num
            inode_block[39]=available_inode_num
            disktools.write_block(available_inode_num,inode_block)
            write_not_available_sign(available_inode_num)
       
        self.fd += 1
        return self.fd

    def getattr(self, path, fh=None):
        available_inode=disktools.read_block(0)
        for i in range(1,8):
            if available_inode[i]:
                inode_data=disktools.read_block(i)
                path_str=inode_data[23:39].decode('utf-8')
                new_path_str=path_str.strip('\0')
                if new_path_str == str(path):

                    self.files[path]['st_mode']=disktools.bytes_to_int(inode_data[0:2])
                    self.files[path]['st_uid']=disktools.bytes_to_int(inode_data[2:4])
                    self.files[path]['st_gid']=disktools.bytes_to_int(inode_data[4:6])
                    self.files[path]['st_nlink']=inode_data[6]
                    self.files[path]['st_size']=disktools.bytes_to_int(inode_data[7:9])
                    self.files[path]['st_ctime']=bytesToFloat(inode_data[9],inode_data[10],inode_data[11],inode_data[12])
                    self.files[path]['st_mtime']=bytesToFloat(inode_data[13],inode_data[14],inode_data[15],inode_data[16])
                    self.files[path]['st_atime']=bytesToFloat(inode_data[17],inode_data[18],inode_data[19],inode_data[20])
                    self.files[path]['st_location0']=inode_data[21]
                    self.files[path]['st_location1']=inode_data[22]
                    self.files[path]['st_inode']=inode_data[39]
        if path not in self.files:
            raise FuseOSError(ENOENT)
        return self.files[path]

    def getxattr(self, path, name, position=0):
        attrs = self.files[path].get('attrs', {})
        try:
            return attrs[name]
        except KeyError:
            return ''       # Should return ENOATTR

    def listxattr(self, path):
        attrs = self.files[path].get('attrs', {})
        return attrs.keys()

    def mkdir(self, path, mode):
        self.files[path] = dict(
            st_mode=(S_IFDIR | mode),
            st_nlink=2,
            st_size=0,
            st_ctime=time(),
            st_mtime=time(),
            st_atime=time())

        self.files['/']['st_nlink'] += 1

    def open(self, path, flags):
        self.fd += 1
        return self.fd

    def read(self, path, size, offset, fh):
        data_block0=disktools.read_block(self.files[path]['st_location0'])
        #print(data_block0)
        if self.files[path]['st_location1']:
              data_block0=data_block0+disktools.read_block(self.files[path]['st_location1'])
        self.data[path]=bytes(data_block0[:self.files[path]['st_size']])
        return self.data[path][offset:offset + size]

    def readdir(self, path, fh):

        available_inode=disktools.read_block(0)
        for i in range(1,8):
            if available_inode[i]:
                inode_data=disktools.read_block(i)
                path_str=inode_data[23:39].decode('utf-8')  
                new_path_str=path_str.strip('\0')
                self.files[new_path_str] = dict(
                    st_mode=disktools.bytes_to_int(inode_data[0:2]),
                    st_nlink=inode_data[6],
                    st_size=disktools.bytes_to_int(inode_data[7:9]),
                    st_ctime=bytesToFloat(inode_data[9],inode_data[10],inode_data[11],inode_data[12]),
                    st_mtime=bytesToFloat(inode_data[13],inode_data[14],inode_data[15],inode_data[16]),
                    st_atime=bytesToFloat(inode_data[17],inode_data[18],inode_data[19],inode_data[20]),
                    st_uid=disktools.bytes_to_int(inode_data[2:4]),
                    st_gid=disktools.bytes_to_int(inode_data[4:6]),
                    st_location0=inode_data[21],
                    st_location1=inode_data[22],
                    st_inode=inode_data[39])

        return ['.', '..'] + [x[1:] for x in self.files if x != '/']

    def readlink(self, path):
        return self.data[path]

    def removexattr(self, path, name):
        attrs = self.files[path].get('attrs', {})

        try:
            del attrs[name]
        except KeyError:
            pass        # Should return ENOATTR

    def rename(self, old, new):
        self.data[new] = self.data.pop(old)
        self.files[new] = self.files.pop(old)

    def rmdir(self, path):
        # with multiple level support, need to raise ENOTEMPTY if contains any files
        self.files.pop(path)
        self.files['/']['st_nlink'] -= 1

    def setxattr(self, path, name, value, options, position=0):
        # Ignore options
        attrs = self.files[path].setdefault('attrs', {})
        attrs[name] = value

    def statfs(self, path):
        return dict(f_bsize=512, f_blocks=4096, f_bavail=2048)

    def symlink(self, target, source):
        self.files[target] = dict(
            st_mode=(S_IFLNK | 0o777),
            st_nlink=1,
            st_size=len(source))

        self.data[target] = source

    def truncate(self, path, length, fh=None):
        # make sure extending the file fills in zero bytes
        self.data[path] = self.data[path][:length].ljust(
            length, '\x00'.encode('ascii'))
        self.files[path]['st_size'] = length

    def unlink(self, path):
        format.fill_block(self.files[path]['st_inode'],0)
        if self.files[path]['st_location0']:
            format.fill_block(self.files[path]['st_location0'],0)
        if self.files[path]['st_location1']:
            format.fill_block(self.files[path]['st_location1'],0)
        save_block0=disktools.read_block(0)
        save_block0[self.files[path]['st_inode']]=0
        if self.files[path]['st_location0']:
            save_block0[self.files[path]['st_location0']]=0
        if self.files[path]['st_location1']:
            save_block0[self.files[path]['st_location1']]=0
        disktools.write_block(0,save_block0)
        if self.data[path]:
            self.data.pop(path)
        self.files.pop(path)
        

    def utimens(self, path, times=None):
        now = time()
        atime, mtime = times if times else (now, now)
        self.files[path]['st_atime'] = atime
        self.files[path]['st_mtime'] = mtime
        saved_inode_block=disktools.read_block(self.files[path]['st_inode'])
        saved_inode_block[13:17]=floatToBytes(self.files[path]['st_mtime'])
        saved_inode_block[17:21]=floatToBytes(self.files[path]['st_atime']) 
        disktools.write_block(self.files[path]['st_inode'],saved_inode_block)

    def write(self, path, data, offset, fh):
        self.data[path] = (
            # make sure the data gets inserted at the right offset
            self.data[path][:offset].ljust(offset, '\x00'.encode('ascii'))
            + data
            # and only overwrites the bytes that data is replacing
            + self.data[path][offset + len(data):])
        if offset:
            save_block0=disktools.read_block(0)
            if self.files[path]['st_location0']:
                save_block0[self.files[path]['st_location0']]=0
            if self.files[path]['st_location1']:
                save_block0[self.files[path]['st_location1']]=0
            disktools.write_block(0,save_block0)
        
        if offset and self.files[path]['st_location0']:
            format.fill_block(self.files[path]['st_location0'],0)
        if offset and self.files[path]['st_location1']:
            format.fill_block(self.files[path]['st_location1'],0)
        self.files[path]['st_size'] = len(self.data[path])
        if self.files[path]['st_size']>128:
            logging.info("We do not support big sizes files at the moment")
            raise IOError("File is too big to save!")
        elif self.files[path]['st_size']>64:
            available_data_num0=get_available_block_number(1)
            available_data_num1=get_available_block_number(1,available_data_num0)
            if available_data_num0==0 or available_data_num1==0:
                logging.info("There is not any available data block!")
                raise IOError("There is not any available data block!")
            else:
                disktools.write_block(available_data_num0,self.data[path][:64])
                write_not_available_sign(available_data_num0)
                disktools.write_block(available_data_num1,self.data[path][64:])
                write_not_available_sign(available_data_num1)  
                
                self.files[path]['st_location0']=available_data_num0
                self.files[path]['st_location1']=available_data_num1
                saved_inode_block=disktools.read_block(self.files[path]['st_inode'])
                saved_inode_block[21]=available_data_num0
                saved_inode_block[22]=available_data_num1
                saved_inode_block[7:9]=disktools.int_to_bytes(self.files[path]['st_size'],2)
                disktools.write_block(self.files[path]['st_inode'],saved_inode_block)                
        else:
            available_data_num0=get_available_block_number(1)
            if available_data_num0==0:
                logging.info("There is not any available data block!")
                raise IOError("There is not any available data block!")
            else:
                disktools.write_block(available_data_num0,self.data[path])
                write_not_available_sign(available_data_num0)
                self.files[path]['st_location0']=available_data_num0
                self.files[path]['st_location1']=0
                saved_inode_block=disktools.read_block(self.files[path]['st_inode'])
                saved_inode_block[21]=available_data_num0
                saved_inode_block[22]=0
                saved_inode_block[7:9]=disktools.int_to_bytes(self.files[path]['st_size'],2)
                disktools.write_block(self.files[path]['st_inode'],saved_inode_block)

        
              
        return len(data)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('mount')
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG)
    fuse = FUSE(Memory(), args.mount, foreground=True)
