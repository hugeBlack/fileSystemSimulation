let aa = document.getElementById("navBarHolder")

let fw = document.getElementById("fileListHolder")

let dirList = []


function updateFileList(){
    fetch(
        "/update_file_list"
    ).then( async response =>{
        let f = await response.json()
        if(!f.success){
            alert(f.msg)
            return
        }
        refreshFileList(f.data)
    }
    )
}

function refreshFileList(dataObj){
    aa.innerHTML = ""
    let d=  new DirBar(dataObj.nowDir)
    dirList = dataObj.nowDir
    aa.appendChild(d)
    fw.innerHTML = ""
    if(dataObj.nowDir.length === 0){
        fw.appendChild(new DiskList(dataObj.disks))

    }else{
        fw.appendChild(new FileList(dataObj.files,"/test"))
    }
}


function createDisk(size, diskName){
    fetch(
        "/create_disk",{
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                "size": size,
                "diskName": diskName
            }),
        }
    ).then( async response =>{
        let f = await response.json()
        console.log(f)
        if(!f.success){
            alert(f.msg)
            return
        }
        refreshFileList(f.data)
    }

    )
}

function createFile(fileName){
    fetch(
        "/create_file",{
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                "fileName": fileName
            }),
        }
    ).then( async response =>{
            let f = await response.json()
            console.log(f)
            if(!f.success){
                alert(f.msg)
                return
            }
            refreshFileList(f.data)
        }

    )
}


function createFolder(folderName){
    fetch(
        "/create_folder",{
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                "folderName": folderName
            }),
        }
    ).then( async response =>{
            let f = await response.json()
            console.log(f)
            if(!f.success){
                alert(f.msg)
                return
            }
            refreshFileList(f.data)
        }

    )
}

function changeDirLevel(level){
    let tmp = dirList.slice(0,level)
    updateDirList(tmp)
}

function appendDir(appendDirName){
    let tmp = Array.from(dirList)
    if(appendDirName === ".."){
        tmp.pop()
    }else if(appendDirName !== "."){
        tmp.push(appendDirName)
    }
    updateDirList(tmp)
}

function updateDirList(tmpDir){
    fetch(
        "/goto",{
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                "directory":tmpDir
            }
            ),
    }
    ).then( async response =>{
            let f = await response.json()
            if(!f.success){
                alert(f.msg)
                return
            }
            refreshFileList(f.data)
        }
    )
}

updateFileList()


function renameFile(oldName,newName){
    fetch(
        "/rename",{
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                "oldName": oldName,
                "newName": newName
                }
            ),
        }
    ).then( async response =>{
            let f = await response.json()
            if(!f.success){
                alert(f.msg)
                return
            }
            refreshFileList(f.data)
        }
    )
}