import io
import struct
import math
import hashlib
from helpers import BitMapHelper
import time
from random import randbytes


def toBytes(v: int):
    return bytearray(struct.pack("q", v))


class HbDisk:
    def __init__(self, dataBlockCount: int = 0, inodeCount: int = 0, fileSize: int = 0,
                 reader: io.BufferedIOBase = None):
        self.streamPtr = 0
        if reader is not None:
            self.diskSize = fileSize
            self.dataBlockCount, self.inodeCount, self.dataBlockLeft, self.inodeLeft = struct.unpack("q",
                                                                                                     self.read(32))

        else:
            self.diskSize = 0
            self.dataBlockCount = dataBlockCount
            self.inodeCount = inodeCount
            self.dataBlockLeft = dataBlockCount
            self.inodeLeft = inodeCount
            self.file = io.BytesIO()
            # 初始化GDT
            self.write(toBytes(dataBlockCount))
            self.write(toBytes(inodeCount))
            self.write(toBytes(dataBlockCount))
            self.write(toBytes(inodeCount))
        # 初始化Block bitmap
        blockBitMapLength = math.ceil(self.dataBlockCount / 8)
        self.write(bytes(blockBitMapLength))
        # 初始化Inode Bitmap
        iNodeBitMapLength = math.ceil(self.inodeCount / 8)
        self.write(bytes(iNodeBitMapLength))

        self.gdtPtr = 0
        self.blockBitmapPtr = 32
        self.inodeBitmapPtr = self.blockBitmapPtr + math.ceil(self.dataBlockCount / 8)
        self.inodeTablePtr = self.inodeBitmapPtr + math.ceil(self.inodeCount / 8)
        self.dataTablePtr = self.inodeTablePtr + self.inodeCount * 128

        self.inodeBMHelper = BitMapHelper(self, self.inodeBitmapPtr, iNodeBitMapLength)
        self.blockBMHelper = BitMapHelper(self, self.blockBitmapPtr, blockBitMapLength)

    def allocINode(self):
        i = self.inodeBMHelper.allocZero()
        self.inodeCount -= 1
        ptr = self.getINodePtr(i)
        self.seek(ptr)
        self.write(bytes(128))
        return i

    def allocBlock(self):
        i = self.blockBMHelper.allocZero()
        if i == -1:
            raise Exception("Not Enough Space!")
        self.dataBlockLeft -= 1
        ptr = self.getDataBlockPtr(i)
        self.seek(ptr)
        self.write(bytes(2048))
        return i

    def releaseBlock(self, blockId):
        hasChanged = self.blockBMHelper.setZero(blockId)
        if not hasChanged:
            raise Exception("Attempting to release an already released block.")
        self.dataBlockLeft += 1

    def releaseINode(self, blockId):
        hasChanged = self.inodeBMHelper.setZero(blockId)
        if hasChanged:
            self.inodeLeft += 1

    def getINodePtr(self, inodeNumber: int):
        return self.inodeTablePtr + (inodeNumber << 7)

    def getDataBlockPtr(self, dataBlockNumber: int):
        return self.dataTablePtr + (dataBlockNumber << 11)

    def getDataBlockNum(self, ptr: int):
        return (ptr - self.dataTablePtr) >> 11

    def createFile(self, path: str, name: str):
        pass

    def seek(self, ptr: int):
        self.streamPtr = ptr
        if self.diskSize <= ptr:
            self.file.write(bytes(ptr - self.diskSize + 1))
            self.diskSize = ptr + 1
        self.file.seek(ptr)

    def read(self, length: int) -> bytes:
        if self.diskSize <= self.streamPtr + length:
            self.file.write(bytes(self.streamPtr + length - self.diskSize + 1))
            self.diskSize = self.streamPtr + length + 1
            self.file.seek(self.streamPtr)
        self.streamPtr += length
        return self.file.read(length)

    def write(self, content: bytes):
        if self.diskSize <= self.streamPtr + len(content) + 1:
            self.diskSize = self.streamPtr + len(content) + 1
        self.streamPtr += len(content)
        self.file.write(content)


class INode:
    def __init__(self, disk: HbDisk, inodeNumber: int, fileType: int = 0, isNew=False):
        self.disk = disk
        self.ptr = disk.getINodePtr(inodeNumber)
        disk.seek(self.ptr)
        if isNew:
            self.size = 0
            disk.write(struct.pack("q", 0))
            self.lastModifyTimeStamp = math.floor(time.time() * 1000)
            disk.write(struct.pack("q", self.lastModifyTimeStamp))
            self.fileType = fileType
            disk.write(struct.pack("q", self.fileType))
        else:
            self.size = struct.unpack("q", disk.read(8))[0]
            self.lastModifyTimeStamp = struct.unpack("q", disk.read(8))[0]
            self.fileType = struct.unpack("q", disk.read(8))[0]

    def save(self):
        self.disk.write(struct.pack("q", self.size))
        self.disk.write(struct.pack("q", self.lastModifyTimeStamp))

    def getDirBlockPtr(self, dirBlockIndex: int):
        self.disk.seek(self.ptr + 24 + dirBlockIndex * 8)
        return struct.unpack("q", self.disk.read(8))[0]

    def saveDirBlockPtr(self, dirBlockIndex: int, ptr: int):
        self.disk.seek(self.ptr + 24 + dirBlockIndex * 8)
        self.disk.write(struct.pack("q", ptr))

    def getIndirectBlockPtr(self):
        self.disk.seek(self.ptr + 104)
        return struct.unpack("q", self.disk.read(8))[0]

    def saveIndirectBlockPtr(self, ptr: int):
        self.disk.seek(self.ptr + 104)
        self.disk.write(struct.pack("q", ptr))

    def getDoubleIndirectBlockPtr(self):
        self.disk.seek(self.ptr + 112)
        return struct.unpack("q", self.disk.read(8))[0]

    def saveDoubleIndirectBlockPtr(self, ptr: int):
        self.disk.seek(self.ptr + 112)
        self.disk.write(struct.pack("q", ptr))

    def getThirdIndirectBlockPtr(self):
        self.disk.seek(self.ptr + 120)
        return struct.unpack("q", self.disk.read(8))[0]

    def saveThirdIndirectBlockPtr(self, ptr: int):
        self.disk.seek(self.ptr + 120)
        self.disk.write(struct.pack("q", ptr))


class HbFile:
    def __init__(self, disk: HbDisk, path: str, inode: INode):
        self.disk = disk
        self.path = path
        self.inode = inode
        # 当前文件的指针
        self.nowPtr = 0
        # 当前找到了文件的第几个快
        self.nowBlockId = -1
        # 当前文件块在disk上的起始地址
        self.nowBlockStartPtr = -1

    def getBlockStartPtrOrAlloc(self, blockId):
        if blockId <= 9:
            ptr0 = self.inode.getDirBlockPtr(blockId)
            if ptr0 == 0:
                ptr0 = self.disk.getDataBlockPtr(self.disk.allocBlock())
                self.inode.saveDirBlockPtr(blockId, ptr0)
            return ptr0

        if blockId <= 9 + 256:
            ptr1 = self.inode.getIndirectBlockPtr()
            if ptr1 == 0:
                ptr1 = self.disk.getDataBlockPtr(self.disk.allocBlock())
                self.inode.saveIndirectBlockPtr(ptr1)
            blockIdL1 = blockId - 10
            self.disk.seek(ptr1 + blockIdL1 * 8)
            ptr0 = struct.unpack("q", self.disk.read(8))[0]
            if ptr0 == 0:
                ptr0 = self.disk.getDataBlockPtr(self.disk.allocBlock())
                self.disk.seek(ptr1 + blockIdL1 * 8)
                self.disk.write(struct.pack("q", ptr0))
            return ptr0

        if blockId <= 9 + 256 + 256 * 256:
            ptr2 = self.inode.getDoubleIndirectBlockPtr()
            if ptr2 == 0:
                ptr2 = self.disk.getDataBlockPtr(self.disk.allocBlock())
                self.inode.saveDoubleIndirectBlockPtr(ptr2)
            blockIdL2 = math.floor((blockId - 10 - 256) / 256)
            self.disk.seek(ptr2 + blockIdL2 * 8)
            ptr1 = struct.unpack("q", self.disk.read(8))[0]
            if ptr1 == 0:
                ptr1 = self.disk.getDataBlockPtr(self.disk.allocBlock())
                self.disk.seek(ptr2 + blockIdL2 * 8)
                self.disk.write(struct.pack("q", ptr1))
            blockIdL1 = (blockId - 10) % 256
            self.disk.seek(ptr1 + blockIdL1 * 8)
            ptr0 = struct.unpack("q", self.disk.read(8))[0]
            if ptr0 == 0:
                ptr0 = self.disk.getDataBlockPtr(self.disk.allocBlock())
                self.disk.seek(ptr1 + blockIdL1 * 8)
                self.disk.write(struct.pack("q", ptr0))
            return ptr0

        if blockId <= 9 + 256 + 256 * 256 + 256 * 256 * 256:
            ptr3 = self.inode.getThirdIndirectBlockPtr()
            if ptr3 == 0:
                ptr3 = self.disk.getDataBlockPtr(self.disk.allocBlock())
                self.inode.saveThirdIndirectBlockPtr(ptr3)
            blockIdL3 = math.floor((blockId - 10 - 256 - 65536) / 65536)
            self.disk.seek(ptr3 + blockIdL3 * 8)
            ptr2 = struct.unpack("q", self.disk.read(8))[0]
            if ptr2 == 0:
                ptr2 = self.disk.getDataBlockPtr(self.disk.allocBlock())
                self.disk.seek(ptr3 + blockIdL3 * 8)
                self.disk.write(struct.pack("q", ptr2))
            blockIdL2 = (blockId - 10 - 256) % 65536
            self.disk.seek(ptr2 + blockIdL2 * 8)
            ptr1 = struct.unpack("q", self.disk.read(8))[0]
            if ptr1 == 0:
                ptr1 = self.disk.getDataBlockPtr(self.disk.allocBlock())
                self.disk.seek(ptr2 + blockIdL2 * 8)
                self.disk.write(struct.pack("q", ptr1))
            blockIdL1 = (blockId - 10) % 256
            self.disk.seek(ptr1 + blockIdL1 * 8)
            ptr0 = struct.unpack("q", self.disk.read(8))[0]
            if ptr0 == 0:
                ptr0 = self.disk.getDataBlockPtr(self.disk.allocBlock())
                self.disk.seek(ptr1 + blockIdL1 * 8)
                self.disk.write(struct.pack("q", ptr0))
            return ptr0

    # 释放文件的一个块，如果这个块是上一级的第一个块，则上一级所占的空间也会被释放
    def releaseIfUsed(self, blockId):
        if blockId <= 9:
            ptr0 = self.inode.getDirBlockPtr(blockId)
            if ptr0 != 0:
                self.disk.releaseBlock(self.disk.getDataBlockNum(ptr0))
                self.inode.saveDirBlockPtr(blockId, 0)
            return

        # 通过一级指针释放占用
        if blockId <= 9 + 256:
            # 先找到一级指针块
            ptr1 = self.inode.getIndirectBlockPtr()
            # 如果一级指针块不存在就直接return
            if ptr1 == 0:
                return
            # 计算是一级指针的第几个块
            blockIdL1 = blockId - 10
            # 获取一级指针指向的块地址
            self.disk.seek(ptr1 + blockIdL1 * 8)
            ptr0 = struct.unpack("q", self.disk.read(8))[0]
            # 释放一级指针指向的块（如果有）
            if ptr0 != 0:
                self.disk.releaseBlock(self.disk.getDataBlockNum(ptr0))
                # 把一级指针的块地址设成0
                self.disk.seek(ptr1 + blockIdL1 * 8)
                self.disk.write(bytes(8))
            # 如果一级指针空了，就释放一级指针块
            if blockIdL1 == 0:
                self.disk.releaseBlock(self.disk.getDataBlockNum(ptr1))
                self.inode.saveIndirectBlockPtr(0)
            return

        if blockId <= 9 + 256 + 256 * 256:
            ptr2 = self.inode.getDoubleIndirectBlockPtr()
            if ptr2 == 0:
                return

            blockIdL2 = math.floor((blockId - 10 - 256) / 256)
            self.disk.seek(ptr2 + blockIdL2 * 8)
            ptr1 = struct.unpack("q", self.disk.read(8))[0]
            if ptr1 == 0:
                return

            blockIdL1 = (blockId - 10) % 256
            self.disk.seek(ptr1 + blockIdL1 * 8)
            ptr0 = struct.unpack("q", self.disk.read(8))[0]
            if ptr0 == 0:
                return

            self.disk.releaseBlock(self.disk.getDataBlockNum(ptr0))
            self.disk.seek(ptr1 + blockIdL1 * 8)
            self.disk.write(bytes(8))

            if blockIdL1 == 0:
                self.disk.releaseBlock(self.disk.getDataBlockNum(ptr1))
                self.disk.seek(ptr2 + blockIdL2 * 8)
                self.disk.write(bytes(8))

            if blockIdL2 == 0:
                self.disk.releaseBlock(self.disk.getDataBlockNum(ptr2))
                self.inode.saveDoubleIndirectBlockPtr(0)

            return

        if blockId <= 9 + 256 + 256 * 256 + 256 * 256 * 256:
            ptr3 = self.inode.getThirdIndirectBlockPtr()
            if ptr3 == 0:
                return

            blockIdL3 = math.floor((blockId - 10 - 256 - 65536) / 65536)
            self.disk.seek(ptr3 + blockIdL3 * 8)
            ptr2 = struct.unpack("q", self.disk.read(8))[0]
            if ptr2 == 0:
                return

            blockIdL2 = (blockId - 10 - 256) % 65536
            self.disk.seek(ptr2 + blockIdL2 * 8)
            ptr1 = struct.unpack("q", self.disk.read(8))[0]
            if ptr1 == 0:
                return

            blockIdL1 = (blockId - 10) % 256
            self.disk.seek(ptr1 + blockIdL1 * 8)
            ptr0 = struct.unpack("q", self.disk.read(8))[0]
            if ptr0 == 0:
                return

            self.disk.releaseBlock(self.disk.getDataBlockNum(ptr0))
            self.disk.seek(ptr1 + blockIdL1 * 8)
            self.disk.write(bytes(8))

            if blockIdL1 == 0:
                self.disk.releaseBlock(self.disk.getDataBlockNum(ptr1))
                self.disk.seek(ptr2 + blockIdL2 * 8)
                self.disk.write(bytes(8))

            if blockIdL2 == 0:
                self.disk.releaseBlock(self.disk.getDataBlockNum(ptr2))
                self.disk.seek(ptr3 + blockIdL3 * 8)
                self.disk.write(bytes(8))

            if blockIdL3 == 0:
                self.disk.releaseBlock(self.disk.getDataBlockNum(ptr3))
                self.inode.saveThirdIndirectBlockPtr(0)

    def resize(self, newSize: int):
        nowBlockCount = math.ceil(self.inode.size / 2048)
        if newSize >= nowBlockCount * 2048:
            for i in range(nowBlockCount, math.ceil(newSize / 2048)):
                self.getBlockStartPtrOrAlloc(i)
                self.inode.size += 2048
        elif newSize <= nowBlockCount * 2048 - 2048:
            for i in range(nowBlockCount - 1, math.ceil(newSize / 2048) - 1, -1):
                self.releaseIfUsed(i)
                self.inode.size -= 2048
        self.inode.size = newSize

    def getSize(self):
        return self.inode.size

    def seek(self, ptr: int):
        if ptr < 0:
            raise Exception("Pointer of a file should be greater than 0.")
        if ptr >= self.inode.size:
            self.resize(ptr + 1)
        self.nowPtr = ptr

    def loadBlockPtr(self):
        # 如果指针对应的块还没有找到，则找到对应的块并缓存指针
        if self.nowBlockId == -1 or not ((self.nowBlockId >> 11) < self.nowPtr < ((self.nowBlockId + 1) >> 11)):
            newBid = self.nowPtr >> 11
            self.nowBlockStartPtr = self.getBlockStartPtrOrAlloc(newBid)
            self.nowBlockId = newBid

    def read(self, readLength=0):
        result = bytes(0)
        if readLength <= 0:
            raise Exception("Read length should be greater than 0.")
        if readLength == 0:
            readLength = self.inode.size
        readLength = min(self.inode.size - self.nowPtr - 1, readLength)
        while readLength > 0:
            self.loadBlockPtr()
            readLengthInBlock = min(2048 - self.nowPtr % 2048, readLength)
            self.disk.seek(self.nowBlockStartPtr + self.nowPtr % 2048)
            self.nowPtr += readLengthInBlock
            result += self.disk.read(readLengthInBlock)
            readLength -= readLengthInBlock
        return result

    def write(self, content: bytes, w=False):
        if w:
            self.nowPtr = 0
            self.resize(len(content))
        elif self.inode.size < len(content) + self.nowPtr + 1:
            self.resize(len(content) + self.nowPtr + 1)

        # writeLenTotal = len(content)
        writeStartIndex = 0
        lengthLeft = len(content)
        while lengthLeft > 0:
            writeLength = min(lengthLeft, 2048 - self.nowPtr % 2048)
            self.loadBlockPtr()
            self.disk.seek(self.nowBlockStartPtr + self.nowPtr % 2048)
            self.disk.write(content[writeStartIndex:writeStartIndex + writeLength])
            self.nowPtr += writeLength
            writeStartIndex += writeLength
            lengthLeft -= writeLength


class HbFolder(HbFile):
    def __init__(self, disk: HbDisk, path: str, inode: INode):
        super().__init__(disk, path, inode)


# 24block 8inode
dk = HbDisk(500, 8)
a = dk.allocINode()
inode = INode(dk, a, 0, True)
f = HbFile(dk, "", inode)
data = randbytes(432000)
data2 = randbytes(11450)

f.write(data)
f.write(data2)
f.seek(0)
data3 = f.read(432000 + 11450)
print(hashlib.sha1(data + data2).hexdigest())
print(hashlib.sha1(data3).hexdigest())