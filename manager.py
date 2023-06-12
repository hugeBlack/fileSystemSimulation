from hbdisk import HbDisk, HbFile, HbFolder, HbDirEntry


class DiskManager:
    def __init__(self, disk: HbDisk):
        self.disk = disk
        self.dirList = []
        self.rootFolder = HbFolder(self.disk, "", self.disk.rootInode)
        self.gotoDir("/")

    def gotoDir(self, path: str):
        if path[-1] == "/":
            path = path[:-1]
        dirs = path.split("/")
        for i, dirName in enumerate(dirs):
            if i == 0:
                if dirName != '':
                    raise Exception("Path should start with /")
                else:
                    self.dirList = [self.rootFolder]
            else:
                if dirName == '':
                    raise Exception("Folder should have name.")
                else:
                    f = self.dirList[-1].getFile(dirName)
                    if type(f) != HbFolder:
                        raise Exception("Path contain file.")
                    self.dirList.append(f)

    def getFile(self, fileName: str)->HbFile:
        return self.dirList[-1].getFile(fileName)

    def createFile(self, fileName: str):
        return self.dirList[-1].createFile(fileName)

    def createFolder(self, fileName: str):
        return self.dirList[-1].createDir(fileName)

    def deleteFile(self, fileName: str, recursive: bool = False):
        self.dirList[-1].deleteSubFile(fileName,recursive)

    def listFile(self):
        for entry in self.dirList[-1].fileList:
            print(f"{entry.fileType}:{entry.fileName} ", end='')
        print()


if __name__ == "__main__":
    dk = HbDisk(500, 100)
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
    f = dm.createFile("testFile")
    f.write("sdsdssdsdsd".encode())
    print(f.getSize())
    f2 = dm.createFile("testFile2")
    f2.write("sdsdssdsdsd".encode())
    dm.listFile()
    dm.deleteFile("testFile")
    dm.listFile()
    dm.gotoDir('/')
    dm.deleteFile("mf2", True)
    dm.listFile()
    print(dk.inodeLeft)
    print(dk.dataBlockLeft)
