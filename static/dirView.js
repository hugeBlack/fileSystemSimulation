aa = document.getElementById("navBarHolder")

d=  new DirBar(["aaa","sss","ddd","fff"])
aa.appendChild(d)

fw = document.getElementById("fileListHolder")

fileList = [
    {
        name : "file1",
        isDir: false,
        lastModifiedTimeStamp: 1145141919,
        size: 9999999,
        path: "/test/file1"
    },
    {
        name : "dir1",
        isDir: true,
        lastModifiedTimeStamp: 1145141919,
        size: 0,
        path: "/test/dir1"
    },
    {
        name : "file2",
        isDir: false,
        lastModifiedTimeStamp: 114514919,
        size: 99999,
        path: "/test/file1"
    }
]

fw.appendChild(new FileList(fileList,"/test"))