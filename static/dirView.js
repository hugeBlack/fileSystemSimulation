let aa = document.getElementById("navBarHolder")

let fw = document.getElementById("fileListHolder")

let dirList = []

let controlBarDom = document.getElementById("controlBar")


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
        controlBarDom.classList.add("diskMode")

    }else{
        fw.appendChild(new FileList(dataObj.files,"/test"))
        controlBarDom.classList.remove("diskMode")
    }
}


function createDisk(){
    let diskName = prompt("请输入空间名：","新建空间")
    let size = Number(prompt("请输入空间大小（单位：MiB）：","100"))
    if (isNaN(size)){
        alert("空间大小应该是数字！")
        return
    }
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

function createFile(){
    let fileName = prompt("请输入文件名：","新建文本文件.txt")
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
            if(!f.success){
                alert(f.msg)
                return
            }
            refreshFileList(f.data)
        }

    )
}


function createFolder(){
    let folderName = prompt("请输入目录名：","新建文件夹")
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

function deleteFile(fileName, fileType){
    fetch(
        "/delete",{
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                    "fileName": fileName,
                    "fileType": fileType
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


function openFile(fileName){
    fetch(
        "/open_file",{
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                    "fileName": fileName,
                }
            ),
        }
    ).then( async response =>{
        let f = await response.json()
        if(!f.success){
            alert(f.msg)
            return
        }
        console.log(f.data)
        window.open("/fileView.html?path=" + encodeURIComponent(f.data.filePath))
    }
    )
}


let formDom = document.getElementById("fileUploadForm")
let fileInput = formDom.querySelector("input")
function uploadFile(){
    if(fileInput.value === "") return
    let formData = new FormData(formDom);
    fetch(
        "/upload",{
            method: "POST",
            body: formData
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

function powerOff(){
    let c = confirm("确定要关闭系统吗？")
    if(!c) return
    fetch(
        "/powerOff",{
            method: "POST",
        }
    ).then( async response =>{
            let f = await response.json()
            if(!f.success){
                alert(f.msg)
            }
        }
    )
    window.close()
}

updateFileList()