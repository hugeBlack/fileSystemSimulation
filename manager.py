import os

from hbdisk import HbDisk, HbFile, HbFolder, HbDirEntry, INode


class DiskManager:
    def __init__(self, disk: HbDisk):
        self.disk = disk
        self.rootFolder = HbFolder(self.disk, "", self.disk.rootInode)
        self.dirList = [self.rootFolder]
        self.dirNameList = []

    def gotoDir(self, dirs):
        newDirList = [self.rootFolder]
        for i, dirName in enumerate(dirs):
            nowFolder = newDirList[-1].getFile(dirName)
            if type(nowFolder) != HbFolder:
                raise Exception("Path contain file.")
            newDirList.append(nowFolder)
        self.dirList = newDirList
        self.dirNameList = dirs

    # 返回这个文件以及其之前所有文件夹的对象
    def getFileAndFullPath(self, fileName: str) -> list[HbFile]:
        ans = self.dirList.copy()
        ans.append(ans[-1].getFile(fileName))
        return ans

    # 检测当前目录下有没有这个文件，没有就抛异常
    def checkFileExist(self, fileName: str):
        self.dirList[-1].findFileEntry(fileName)

    def createFile(self, fileName: str):
        return self.dirList[-1].createFile(fileName)

    def rename(self, oldName, newName):
        self.dirList[-1].renameSubFile(oldName, newName)

    def createFolder(self, fileName: str):
        return self.dirList[-1].createDir(fileName)

    def deleteFile(self, fileName: str, recursive: bool = False):
        self.dirList[-1].deleteSubFile(fileName, recursive)

    def getFileList(self):
        return self.dirList[-1].fileList


class FileOpenCounter:
    def __init__(self, file: HbFile, isLeaf=False):
        self.file = file
        self.counter = 1
        self.isLeaf = isLeaf


class StorageManager:
    def __init__(self, diskMgrList: list[DiskManager] = []):
        self.disks = diskMgrList
        self.nowDisk: DiskManager = None
        self.openedFile = {}

    def switchDisk(self, diskName):
        if self.nowDisk is not None and self.nowDisk.disk.diskName == diskName:
            return
        for disk in self.disks:
            if disk.disk.diskName == diskName:
                self.nowDisk = disk
                return
        raise Exception("Disk with that name not found.")

    def clearDisk(self):
        self.nowDisk = None

    def getDir(self) -> list[str]:
        if self.nowDisk is None:
            return []
        ans = [self.nowDisk.disk.diskName]
        ans += self.nowDisk.dirNameList
        return ans

    def switchDir(self, dirList):
        self.nowDisk.gotoDir(dirList)

    def getDiskReport(self):
        ans = []
        for disk in self.disks:
            ans.append({
                "name": disk.disk.diskName,
                "totalBlocks": disk.disk.dataBlockCount,
                "blocksLeft": disk.disk.dataBlockLeft
            })
        return ans

    def createDisk(self, dataBlockCount, inodeCount, diskName):
        for disk in self.disks:
            if disk.disk.diskName == diskName:
                raise Exception("Disk with that name already exists.")
        newDisk = HbDisk(dataBlockCount, inodeCount, diskName)
        newDm = DiskManager(newDisk)
        self.disks.append(newDm)

    def createFolder(self, folderName: str):
        if self.nowDisk is None:
            raise Exception("You have to open a disk first")
        self.nowDisk.createFolder(folderName)

    def createFile(self, fileName: str):
        if self.nowDisk is None:
            raise Exception("You have to open a disk first")
        return self.nowDisk.createFile(fileName)

    def deleteFile(self, fileName):
        if self.checkFileOpen(fileName) is not None:
            raise Exception("You can't delete an opened file or folder. Close it first.")
        self.nowDisk.deleteFile(fileName)

    def deleteFolder(self, folderName):
        self.nowDisk.deleteFile(folderName, True)

    def renameFile(self, oldName, newName):
        if self.checkFileOpen(oldName) is not None:
            raise Exception("You can't rename an opened file or folder. Close it first.")
        if self.nowDisk is None:
            for disk in self.disks:
                if disk.disk.diskName == oldName:
                    disk.disk.rename(newName)
                    return
            raise Exception("Disk with that name does not exist.")
        self.nowDisk.rename(oldName, newName)

    def getFileList(self):
        if self.nowDisk is None:
            return []
        ans = []
        ls = self.nowDisk.getFileList()
        for file in ls:
            inode = INode(self.nowDisk.disk, inodePtr=file.inodePtr)
            ans.append({
                "name": file.fileName,
                "type": file.fileType,
                "size": inode.size,
                "lastModifiedTimeStamp": inode.lastModifyTimeStamp
            })
        return ans

    def checkFileOpen(self, fileName):
        filePath = '/'.join(self.getDir() + [fileName])
        if filePath in self.openedFile:
            return filePath
        return None

    def openFile(self, fileName):
        self.nowDisk.checkFileExist(fileName)
        fullDir = self.getDir()
        fullDir.append(fileName)
        fullDirObj = self.nowDisk.getFileAndFullPath(fileName)
        # 把这个文件及其上级的所有文件的占用数都+1
        ans = '/'.join(fullDir)
        fullDirLenMinusOne = len(fullDir) - 1
        for i in range(fullDirLenMinusOne, -1, -1):
            filePath = '/'.join(fullDir[:i + 1])
            if filePath not in self.openedFile:
                file = fullDirObj[i]
                self.openedFile[filePath] = FileOpenCounter(file, i == 0)
            else:
                if i == fullDirLenMinusOne:
                    return
                self.openedFile[filePath].counter += 1
        return ans

    def closeFile(self, filePath: str):
        if filePath not in self.openedFile or self.openedFile[filePath].isLeaf:
            raise Exception("File is not opened!")
        dirList = filePath.split('/')
        for i in range(0, len(dirList)):
            filePath = '/'.join(dirList[:i + 1])
            if filePath not in self.openedFile:
                raise Exception("Parent dir not in openedList, this should not happen!")
            else:
                self.openedFile[filePath].counter -= 1
                if self.openedFile[filePath].counter == 0:
                    self.openedFile.pop(filePath)

    def readAll(self, filePath):
        if filePath not in self.openedFile:
            raise Exception("File not opened. Open it in dirView first.")
        file: HbFile = self.openedFile[filePath].file
        file.seek(0)
        content = file.read().decode("utf-8")
        return content

    def writeFromStart(self, filePath, content):
        if filePath not in self.openedFile:
            raise Exception("File not opened. Open it in dirView first.")
        file: HbFile = self.openedFile[filePath].file
        file.write(content.encode(), True)

    def uploadNewFile(self, stream, fileName):
        file = self.createFile(fileName)
        file.write(stream.read(), True)

    def downloadFile(self, filePath):
        if filePath not in self.openedFile or self.openedFile[filePath].isLeaf:
            raise Exception("File not opened. Open it in dirView first.")
        file = self.openedFile[filePath].file
        file.seek(0)
        return file

    def powerOff(self):
        for disk in self.disks:
            disk.disk.saveToDisk()
        os._exit(0)


if __name__ == "__main__":
    dk = HbDisk(500, 100, "MYDISK")
    dk.rename("MYNewDisk")
    dm = DiskManager(dk)
    print(dk)
    dm.createFolder("mf1")
    dm.createFolder("mf3")
    print(dk.inodeLeft)
    print(dk.dataBlockLeft)
    dm.createFolder("mf2")

    dm.listFile()
    dm.gotoDir("/mf2")
    dm.createFolder("c")
    dm.createFolder("c2")
    dm.createFolder("c3")
    dm.gotoDir("/mf2/c3")
    f = dm.createFile("testFile")
    f.write("sdsdssdsdsd".encode())
    print(f.getSize())
    f2 = dm.createFile("testFile2")
    f2.write("sdsdssdsdsd".encode())

    bio = dk.file
    bio.seek(0)
    dk2 = HbDisk(reader=bio, fileSize=dk.diskSize)
    print(dk2.diskName)
    dm2 = DiskManager(dk2)
    dm2.gotoDir("/mf2/c3")
    dm2.listFile()
    f2 = dm2.getFile("testFile2")
    print(f2.read().decode("utf-8"))
