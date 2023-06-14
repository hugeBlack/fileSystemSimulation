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

    def getFile(self, fileName: str) -> HbFile:
        return self.dirList[-1].getFile(fileName)

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


class StorageManager:
    def __init__(self, diskMgrList: list[DiskManager] = []):
        self.disks = diskMgrList
        self.nowDisk: DiskManager = None

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

    def getDir(self):
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
        self.nowDisk.createFile(fileName)

    def deleteFile(self, fileName):
        self.nowDisk.deleteFile(fileName)

    def deleteFolder(self, folderName):
        self.nowDisk.deleteFile(folderName, True)

    def renameFile(self, oldName, newName):
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
