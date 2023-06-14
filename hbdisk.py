import io
import struct
import math
import hashlib
from typing import BinaryIO

from helpers import BitMapHelper
import time
from random import randbytes


def toBytes(v: int):
    return bytearray(struct.pack("q", v))


class HbDisk:
    def __init__(self, dataBlockCount: int = 0, inodeCount: int = 0,
                 diskName: str = "",
                 fileSize: int = 0,
                 reader: BinaryIO = None):
        self.streamPtr = 0
        # 计算gdt表各参数位置
        self.gdtPtr = 0
        self.diskNameLenPtr = 32
        self.diskNamePtr = self.diskNameLenPtr + 1
        self.hasDiskFile = False

        if reader is not None:
            self.hasDiskFile = True
            self.file = reader
            self.diskSize = fileSize
            self.dataBlockCount, self.inodeCount, self.dataBlockLeft, self.inodeLeft = struct.unpack("qqqq",
                                                                                                     self.read(32))
            self.diskNameLength = self.read(1)[0]
            self.diskName = self.read(self.diskNameLength).decode("utf-8")
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
            # 初始化磁盘名
            encodedName = diskName.encode()
            self.write(bytes([len(encodedName)]))
            self.write(bytes(255))
            self.seek(self.diskNamePtr)
            self.write(encodedName)
            self.diskName = diskName
        self.blockBitmapPtr = self.diskNamePtr + 255
        self.seek(self.blockBitmapPtr)
        # 初始化Block bitmap
        blockBitMapLength = math.ceil(self.dataBlockCount / 8)
        self.write(bytes(blockBitMapLength))
        # 初始化Inode Bitmap
        iNodeBitMapLength = math.ceil(self.inodeCount / 8)
        self.write(bytes(iNodeBitMapLength))
        # 计算4个表的起始地址
        self.inodeBitmapPtr = self.blockBitmapPtr + math.ceil(self.dataBlockCount / 8)
        self.inodeTablePtr = self.inodeBitmapPtr + math.ceil(self.inodeCount / 8)
        self.dataTablePtr = self.inodeTablePtr + self.inodeCount * 128

        self.inodeBMHelper = BitMapHelper(self, self.inodeBitmapPtr, iNodeBitMapLength)
        self.blockBMHelper = BitMapHelper(self, self.blockBitmapPtr, blockBitMapLength)

        # 建立根目录INode
        if reader is not None:
            self.rootInode = INode(self, 0)
        else:
            a = self.allocINode()
            self.rootInode = INode(self, a, isNew=True)

    def allocINode(self):
        i = self.inodeBMHelper.allocZero()
        self.inodeLeft -= 1
        ptr = self.getINodePtr(i)
        self.seek(ptr)
        self.write(bytes(128))
        self.saveDGT()
        return i

    def allocBlock(self):
        i = self.blockBMHelper.allocZero()
        if i == -1:
            raise Exception("Not Enough Space!")
        self.dataBlockLeft -= 1
        ptr = self.getDataBlockPtr(i)
        self.seek(ptr)
        self.write(bytes(2048))
        self.saveDGT()
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

    def getINodeNumber(self, inodePtr: int):
        return (inodePtr - self.inodeTablePtr) >> 7

    def getDataBlockPtr(self, dataBlockNumber: int):
        return self.dataTablePtr + (dataBlockNumber << 11)

    def getDataBlockNum(self, ptr: int):
        return (ptr - self.dataTablePtr) >> 11

    def saveDGT(self):
        self.seek(0)
        self.write(toBytes(self.dataBlockCount))
        self.write(toBytes(self.inodeCount))
        self.write(toBytes(self.dataBlockLeft))
        self.write(toBytes(self.inodeLeft))

    def rename(self, newName: str):
        encodedName = newName.encode()
        if len(encodedName) > 255:
            raise Exception("Disk name should be no longer than 255.")
        if len(encodedName) == 0:
            raise Exception("Disk name should be longer then 0 char.")
        if newName.find('/') > 0:
            raise Exception("Disk name should not contain '/'.")
        self.diskNameLength = len(encodedName)
        self.diskName = newName

        self.seek(self.diskNameLenPtr)
        self.write(bytes([self.diskNameLength]))
        self.write(encodedName)

    def saveToDisk(self):
        if self.hasDiskFile:
            self.file.close()
            return
        realFile = open(self.diskName + ".hbdk", "xb")
        self.file.seek(0)
        realFile.write(self.file.read())

    def seek(self, ptr: int):
        self.streamPtr = ptr
        if self.diskSize <= ptr:
            self.file.seek(self.diskSize - 1)  # 指针移动到文件尾部！
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
    def __init__(self, disk: HbDisk, inodeNumber: int = -1, inodePtr: int = -1, isNew=False):
        self.disk = disk
        if inodePtr != -1:
            self.ptr = inodePtr
        else:
            self.ptr = disk.getINodePtr(inodeNumber)
        disk.seek(self.ptr)
        if isNew:
            self.size = 0
            disk.write(struct.pack("q", 0))
            self.lastModifyTimeStamp = math.floor(time.time() * 1000)
            disk.write(struct.pack("q", self.lastModifyTimeStamp))
        else:
            self.size = struct.unpack("q", disk.read(8))[0]
            self.lastModifyTimeStamp = struct.unpack("q", disk.read(8))[0]

    def save(self):
        self.disk.seek(self.ptr)
        self.disk.write(struct.pack("q", self.size))
        self.disk.write(struct.pack("q", self.lastModifyTimeStamp))

    def getDirBlockPtr(self, dirBlockIndex: int):
        self.disk.seek(self.ptr + 16 + dirBlockIndex * 8)
        return struct.unpack("q", self.disk.read(8))[0]

    def saveDirBlockPtr(self, dirBlockIndex: int, ptr: int):
        self.disk.seek(self.ptr + 16 + dirBlockIndex * 8)
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
        if blockId <= 10:
            ptr0 = self.inode.getDirBlockPtr(blockId)
            if ptr0 == 0:
                ptr0 = self.disk.getDataBlockPtr(self.disk.allocBlock())
                self.inode.saveDirBlockPtr(blockId, ptr0)
            return ptr0

        if blockId <= 10 + 256:
            ptr1 = self.inode.getIndirectBlockPtr()
            if ptr1 == 0:
                ptr1 = self.disk.getDataBlockPtr(self.disk.allocBlock())
                self.inode.saveIndirectBlockPtr(ptr1)
            blockIdL1 = blockId - 11
            self.disk.seek(ptr1 + blockIdL1 * 8)
            ptr0 = struct.unpack("q", self.disk.read(8))[0]
            if ptr0 == 0:
                ptr0 = self.disk.getDataBlockPtr(self.disk.allocBlock())
                self.disk.seek(ptr1 + blockIdL1 * 8)
                self.disk.write(struct.pack("q", ptr0))
            return ptr0

        if blockId <= 10 + 256 + 256 * 256:
            ptr2 = self.inode.getDoubleIndirectBlockPtr()
            if ptr2 == 0:
                ptr2 = self.disk.getDataBlockPtr(self.disk.allocBlock())
                self.inode.saveDoubleIndirectBlockPtr(ptr2)
            blockIdL2 = math.floor((blockId - 11 - 256) / 256)
            self.disk.seek(ptr2 + blockIdL2 * 8)
            ptr1 = struct.unpack("q", self.disk.read(8))[0]
            if ptr1 == 0:
                ptr1 = self.disk.getDataBlockPtr(self.disk.allocBlock())
                self.disk.seek(ptr2 + blockIdL2 * 8)
                self.disk.write(struct.pack("q", ptr1))
            blockIdL1 = (blockId - 11) % 256
            self.disk.seek(ptr1 + blockIdL1 * 8)
            ptr0 = struct.unpack("q", self.disk.read(8))[0]
            if ptr0 == 0:
                ptr0 = self.disk.getDataBlockPtr(self.disk.allocBlock())
                self.disk.seek(ptr1 + blockIdL1 * 8)
                self.disk.write(struct.pack("q", ptr0))
            return ptr0

        if blockId <= 10 + 256 + 256 * 256 + 256 * 256 * 256:
            ptr3 = self.inode.getThirdIndirectBlockPtr()
            if ptr3 == 0:
                ptr3 = self.disk.getDataBlockPtr(self.disk.allocBlock())
                self.inode.saveThirdIndirectBlockPtr(ptr3)
            blockIdL3 = math.floor((blockId - 11 - 256 - 65536) / 65536)
            self.disk.seek(ptr3 + blockIdL3 * 8)
            ptr2 = struct.unpack("q", self.disk.read(8))[0]
            if ptr2 == 0:
                ptr2 = self.disk.getDataBlockPtr(self.disk.allocBlock())
                self.disk.seek(ptr3 + blockIdL3 * 8)
                self.disk.write(struct.pack("q", ptr2))
            blockIdL2 = (blockId - 11 - 256) % 65536
            self.disk.seek(ptr2 + blockIdL2 * 8)
            ptr1 = struct.unpack("q", self.disk.read(8))[0]
            if ptr1 == 0:
                ptr1 = self.disk.getDataBlockPtr(self.disk.allocBlock())
                self.disk.seek(ptr2 + blockIdL2 * 8)
                self.disk.write(struct.pack("q", ptr1))
            blockIdL1 = (blockId - 11) % 256
            self.disk.seek(ptr1 + blockIdL1 * 8)
            ptr0 = struct.unpack("q", self.disk.read(8))[0]
            if ptr0 == 0:
                ptr0 = self.disk.getDataBlockPtr(self.disk.allocBlock())
                self.disk.seek(ptr1 + blockIdL1 * 8)
                self.disk.write(struct.pack("q", ptr0))
            return ptr0

    # 释放文件的一个块，如果这个块是上一级的第一个块，则上一级所占的空间也会被释放
    def releaseIfUsed(self, blockId):
        if blockId <= 10:
            ptr0 = self.inode.getDirBlockPtr(blockId)
            if ptr0 != 0:
                self.disk.releaseBlock(self.disk.getDataBlockNum(ptr0))
                self.inode.saveDirBlockPtr(blockId, 0)
            return

        # 通过一级指针释放占用
        if blockId <= 10 + 256:
            # 先找到一级指针块
            ptr1 = self.inode.getIndirectBlockPtr()
            # 如果一级指针块不存在就直接return
            if ptr1 == 0:
                return
            # 计算是一级指针的第几个块
            blockIdL1 = blockId - 11
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

        if blockId <= 10 + 256 + 256 * 256:
            ptr2 = self.inode.getDoubleIndirectBlockPtr()
            if ptr2 == 0:
                return

            blockIdL2 = math.floor((blockId - 11 - 256) / 256)
            self.disk.seek(ptr2 + blockIdL2 * 8)
            ptr1 = struct.unpack("q", self.disk.read(8))[0]
            if ptr1 == 0:
                return

            blockIdL1 = (blockId - 11) % 256
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

        if blockId <= 10 + 256 + 256 * 256 + 256 * 256 * 256:
            ptr3 = self.inode.getThirdIndirectBlockPtr()
            if ptr3 == 0:
                return

            blockIdL3 = math.floor((blockId - 11 - 256 - 65536) / 65536)
            self.disk.seek(ptr3 + blockIdL3 * 8)
            ptr2 = struct.unpack("q", self.disk.read(8))[0]
            if ptr2 == 0:
                return

            blockIdL2 = (blockId - 11 - 256) % 65536
            self.disk.seek(ptr2 + blockIdL2 * 8)
            ptr1 = struct.unpack("q", self.disk.read(8))[0]
            if ptr1 == 0:
                return

            blockIdL1 = (blockId - 11) % 256
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
                self.inode.save()
        elif newSize <= nowBlockCount * 2048 - 2048:
            for i in range(nowBlockCount - 1, math.ceil(newSize / 2048) - 1, -1):
                self.releaseIfUsed(i)
                self.inode.size -= 2048
                self.inode.save()
        self.inode.size = newSize

    def getSize(self):
        return self.inode.size

    def seek(self, ptr: int):
        if ptr < 0:
            raise Exception("Pointer of a file should be greater than 0.")
        if ptr > self.inode.size:
            self.resize(ptr)
        self.nowPtr = ptr

    def loadBlockPtr(self):
        # 如果指针对应的块还没有找到，则找到对应的块并缓存指针
        if self.nowBlockId == -1 or not ((self.nowBlockId >> 11) < self.nowPtr < ((self.nowBlockId + 1) >> 11)):
            newBid = self.nowPtr >> 11
            self.nowBlockStartPtr = self.getBlockStartPtrOrAlloc(newBid)
            if self.nowBlockStartPtr < 0:
                raise Exception()
            self.nowBlockId = newBid

    def read(self, readLength=0):
        result = bytes(0)
        if readLength < 0:
            raise Exception("Read length should be greater than 0.")
        if readLength == 0:
            readLength = self.inode.size - self.nowPtr
        readLength = min(self.inode.size - self.nowPtr, readLength)
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
        elif self.inode.size < len(content) + self.nowPtr:
            self.resize(len(content) + self.nowPtr)

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
        self.inode.save()


class HbDirEntry:
    def __init__(self, inodePtr: int, fileType: int, fileName: str):
        self.fileName = fileName
        self.fileType = fileType
        self.inodePtr = inodePtr


class HbFolder(HbFile):
    def __init__(self, disk: HbDisk, path: str, inode: INode):
        super().__init__(disk, path, inode)
        self.fileList: list[HbDirEntry] = []
        if self.getSize() == 0:
            return
        fileListBytes = self.read()
        reader = io.BytesIO(fileListBytes)

        while True:
            aa = reader.read(8)
            if len(aa) == 0:
                return
            inodePtr = struct.unpack("q", aa)[0]
            fileType = reader.read(1)[0]
            fileNameLength = reader.read(1)[0]
            fileName = reader.read(fileNameLength).decode()
            self.fileList.append(HbDirEntry(inodePtr, fileType, fileName))

    def save(self):
        ans = bytes(0)
        for entry in self.fileList:
            ans += struct.pack('q', entry.inodePtr)
            ans += bytes([entry.fileType])
            fileNameBytes = entry.fileName.encode()
            ans += bytes([len(fileNameBytes)])
            ans += fileNameBytes
        self.write(ans, True)

    def findFileEntry(self, fileName: str):
        for entry in self.fileList:
            if entry.fileName == fileName:
                return entry
        return None

    def createDir(self, dirName: str):
        if self.findFileEntry(dirName) is not None:
            raise Exception("File with that name already exists.")
        inode = INode(self.disk, self.disk.allocINode(), isNew=True)
        self.fileList.append(HbDirEntry(inode.ptr, 1, dirName))
        self.save()
        f = HbFolder(self.disk, "", inode)
        # 添加.和..
        f.fileList.append(HbDirEntry(self.inode.ptr, 1, '..'))
        f.fileList.append(HbDirEntry(inode.ptr, 1, "."))
        f.save()

    def createFile(self, fileName):
        if self.findFileEntry(fileName) is not None:
            raise Exception("File with that name already exists.")
        if len(fileName) > 255:
            raise Exception("New name should be no longer than 255.")
        if len(fileName) == 0:
            raise Exception("New name should longer then 0 char.")
        if fileName.find('/') > 0:
            raise Exception("File name should not contain '/'.")
        inode = INode(self.disk, self.disk.allocINode(), isNew=True)
        self.fileList.append(HbDirEntry(inode.ptr, 0, fileName))
        self.save()
        return HbFile(self.disk, "", inode)

    def renameSubFile(self, oldName, newName):
        if len(newName) > 255:
            raise Exception("New name should no longer than 255.")
        if len(newName) == 0:
            raise Exception("New name should be longer then 0 char.")
        if newName.find('/') > 0:
            raise Exception("File name should not contain '/'.")
        entry = self.findFileEntry(oldName)
        if entry is None:
            raise Exception("File with old name not found.")
        entry.fileName = newName
        self.save()

    def deleteSubFile(self, fileName, recursive=False):
        entry = self.findFileEntry(fileName)
        if entry is None:
            raise Exception("File with that name not found.")
        self.deleteEntry(entry, recursive)
        self.fileList.remove(entry)
        self.save()

    def deleteEntry(self, entry, recursive):
        if entry.fileName == '..' or entry.fileName == '.':
            raise "You can't delete this."
        if entry.fileType != 1:
            file = HbFile(self.disk, "", INode(disk=self.disk, inodePtr=entry.inodePtr))
            file.resize(0)
        elif recursive:
            folder = HbFolder(self.disk, "", INode(disk=self.disk, inodePtr=entry.inodePtr))
            folder.deleteAllSubFile()
            folder.resize(0)
        else:
            raise Exception("Folder cannot be deleted without recursive mode.")
        self.disk.releaseINode(self.disk.getINodeNumber(entry.inodePtr))

    def getFile(self, fileName: str):
        entry = self.findFileEntry(fileName)
        if entry is None:
            raise Exception("File with that name not found.")
        if entry.fileType == 0:
            return HbFile(self.disk, "", INode(disk=self.disk, inodePtr=entry.inodePtr))
        elif entry.fileType == 1:
            return HbFolder(self.disk, "", INode(disk=self.disk, inodePtr=entry.inodePtr))

    def deleteAllSubFile(self):
        for entry in self.fileList:
            if entry.fileName != '..' and entry.fileName != '.':
                self.deleteEntry(entry, True)


if __name__ == "__main__":
    # 24block 8inode
    dk = HbDisk(500, 8)

    # f = HbFile(dk, "", inode)
    data = randbytes(432000)
    # data2 = randbytes(11450)
    #
    # f.write(data)
    # f.write(data2)
    # f.seek(0)
