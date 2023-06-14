import os

from hbdisk import HbDisk, HbFile, HbFolder, INode


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
                raise Exception("地址包含文件。")
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
        raise Exception("未找到该空间。")

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
                raise Exception("该空间已存在。")
        newDisk = HbDisk(dataBlockCount, inodeCount, diskName)
        newDm = DiskManager(newDisk)
        self.disks.append(newDm)

    def createFolder(self, folderName: str):
        if self.nowDisk is None:
            raise Exception("你需要先打开一个空间。")
        self.nowDisk.createFolder(folderName)

    def createFile(self, fileName: str):
        if self.nowDisk is None:
            raise Exception("你需要先打开一个空间。")
        return self.nowDisk.createFile(fileName)

    def deleteFile(self, fileName):
        if self.checkFileOpen(fileName) is not None:
            raise Exception("该文件或文件夹已被占用，请关闭占用的文件。")
        self.nowDisk.deleteFile(fileName)

    def deleteFolder(self, folderName):
        self.nowDisk.deleteFile(folderName, True)

    def renameFile(self, oldName, newName):
        if self.checkFileOpen(oldName) is not None:
            raise Exception("该文件或文件夹已被占用，请关闭占用的文件。")
        if self.nowDisk is None:
            for disk in self.disks:
                if disk.disk.diskName == oldName:
                    disk.disk.rename(newName)
                    return
            raise Exception("空间已存在。")
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
            raise Exception("文件未被打开!")
        dirList = filePath.split('/')
        for i in range(0, len(dirList)):
            filePath = '/'.join(dirList[:i + 1])
            if filePath not in self.openedFile:
                raise Exception("Parent dir not in openedList, which should not happen!!")
            else:
                self.openedFile[filePath].counter -= 1
                if self.openedFile[filePath].counter == 0:
                    self.openedFile.pop(filePath)

    def readAll(self, filePath):
        if filePath not in self.openedFile:
            raise Exception("文件未打开。在目录视图中点击文件打开。")
        file: HbFile = self.openedFile[filePath].file
        file.seek(0)
        content = file.read().decode("utf-8")
        return content

    def writeFromStart(self, filePath, content):
        if filePath not in self.openedFile:
            raise Exception("文件未打开。在目录视图中点击文件打开。")
        file: HbFile = self.openedFile[filePath].file
        file.write(content.encode(), True)

    def uploadNewFile(self, stream, fileName):
        file = self.createFile(fileName)
        file.write(stream.read(), True)

    def downloadFile(self, filePath):
        if filePath not in self.openedFile or self.openedFile[filePath].isLeaf:
            raise Exception("文件未打开。在目录视图中点击文件打开。")
        file = self.openedFile[filePath].file
        file.seek(0)
        return file

    def powerOff(self):
        for disk in self.disks:
            disk.disk.saveToDisk()
        os._exit(0)
