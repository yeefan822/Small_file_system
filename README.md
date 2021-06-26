# Small_file_system
This is my own file system which has only a small number of disk blocks (currently 16) and each disk block is currently only 64 bytes long.
The disk is divided into sixteen blocks. I use the first block to store the information for each block. The first to sixteenth bytes represent the status of first to sixteenth blocks. Being 0 means available and 1 means occupied. When a free block is required, we first need to know what sort of data need to be stored. If we want to store some metadata then we are trying to find a free block from the first eight blocks. We loop from the first byte to the eighth byte of the first block. If the corresponding byte in the first block has a value of 0 then that block is available.(For example, if the forth byte is 0 which means the forth block is available).If we want to store some file data then we are trying to find a free block from the last eight blocks. 

I use two var st_location1 and st_location2 to store the information of the location of file data. If the file data for one file is too big for one block to store then we search for another free block to store the rest data. If the file is not big then leave st_location2 equals zero means that no additional block is needed. Both st_location1 and st_location2 are stored with the other file attributes so that the file attributes and file data are connected. Both st_location1 and st_location2 are initially set to be zero when calling the create function as no file data yet. After calling the write function the two attributes will then be updated. For example, I want to find the file data with the file attributes stored in block 5. So I access into block 5 by getattr() and go to slice [21:22] to get the value of st_location1 and st_location2. In this case we assume st_location1 is 10 and st_location2 is 0. This means that the file data is stored in the tenth block so we can then read the tenth block to get the file data.

To run the file system:

Call the disktool.py first

Then call the format.py to format the space

Create a mount directory by running: "python small.py mount" (if using python 2 or python 3 then just use the corresponding command).

A tiny file system will be created and now you can try some commands there(e.g. touch, echo, cat, ls, rm)

You can check the output of your operations by running: "od --address-radix=x -t x1 -a my-disk "
