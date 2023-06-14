class DirItem extends HTMLElement{
    constructor(lastDir,dirLevel,isLast,isRoot = false){
        super()
        this.dirLevel = dirLevel
        this.isLast = isLast
        this.lastDir = lastDir
        this.isRoot = isRoot
    }

    connectedCallback(){
        if(this.isLast){
            this.contentDom = document.createElement("span")
        }else{
            this.contentDom = document.createElement("a")
            this.contentDom.addEventListener("click",evt => this.goto())
        }

        if(this.isRoot){
            let a = document.createElement("i")
            a.classList.add("fas","fa-home")
            this.contentDom.appendChild(a)
        }else{
            this.contentDom.innerHTML = this.lastDir
        }
        this.appendChild(this.contentDom)

    }

    goto(){
        changeDirLevel(this.dirLevel)
    }

}
customElements.define('dir-item', DirItem);

class DirBar extends HTMLElement{
    constructor(dirList){
        super()
        this.dirList = dirList
    }

    connectedCallback(){
        let count = this.dirList.length
        let homeBtn = new DirItem("", 0,false,true)
        this.appendChild(homeBtn)
        for(let i = 0;i<count;i++){
            let a = new DirItem(this.dirList[i], i + 1,i===count-1)
            this.appendChild(a)
        }
    }


}
customElements.define('dir-bar', DirBar);


function TimestampToDate(Timestamp) {
    let date1 = new Date(Timestamp);
    return date1.toLocaleDateString().replace(/\//g, "-") + " " + date1.toTimeString().substr(0, 8);
}

//将字节数转换为合适的单位
function genSizeStr(size){
    let ans
    if(size > 1073741824){
        ans = (size/1073741824).toFixed(2) + "GiB"
    }else if (size > 1048576){
        ans = (size/1048576).toFixed(2) + "MiB"
    }else if (size > 1024){
        ans = (size/1024).toFixed(2) + "KiB"
    }else{
        ans = size + "B"
    }
    return ans
}

class FileItem extends HTMLElement{
    constructor(fileName,isDir,lastModifiedTimestamp,size,isHeader = false){
        super()
        this.fileName = fileName
        this.isDir = isDir
        this.lastModifiedTimestamp = lastModifiedTimestamp
        this.size = size
        this.isHeader = isHeader
    }

    connectedCallback(){
        let templateElem = document.getElementById("fileItemTemplate");
        const templateContent = templateElem.content;
        this.appendChild(templateContent.cloneNode(true));
        if(this.isHeader){
            this.querySelector(".fileName").innerHTML = "文件名"
            this.querySelector(".fileSize").innerHTML = "文件大小"
            this.querySelector(".fileLastModified").innerHTML = "上次修改"
            this.querySelector(".deleteButton").remove()
            this.querySelector(".renameButton").remove()
            return
        }
        this.fileNameDom = this.querySelector(".fileName")
        this.fileNameDom = this.querySelector(".fileName")
        this.fileSizeDom = this.querySelector(".fileSize")

        this.fileNameDom.innerHTML = this.fileName
        if(this.isDir){
            this.querySelector(".fileIcon").classList.add("fas","fa-folder")
            this.fileNameDom.addEventListener("click",evt => this.gotoDir())
        }else{
            this.querySelector(".fileIcon").classList.add("fas","fa-file")
            this.fileNameDom.addEventListener("click",evt => this.openMe())
            this.fileSizeDom.innerHTML = genSizeStr(this.size)
        }
        if(this.fileName!==".." && this.fileName!=="."){
            this.querySelector(".fileLastModified").innerHTML = TimestampToDate(this.lastModifiedTimestamp)
        }else{
            this.querySelector(".deleteButton").remove()
            this.querySelector(".renameButton").remove()
        }
        let rb = this.querySelector(".renameButton")
        if(rb){
            rb.addEventListener("click", evt => this.startRename())
            this.newNameInput = this.querySelector(".newFileNameInput")

        }

        let db = this.querySelector(".deleteButton")
        if(db){
            db.addEventListener("click", evt => this.deleteMe())
        }

        this.querySelector(".submitRenameBtn").addEventListener("click",evt => this.submitRename())
        this.querySelector(".cancelRenameBtn").addEventListener("click",evt => this.cancelRename())

    }

    startRename(){
        this.classList.add("editingName")
        this.newNameInput.value = this.fileName
        this.newNameInput.select()

    }

    cancelRename(){
        this.classList.remove("editingName")
    }

    submitRename(){
        let oldName = this.fileName
        this.classList.remove("editingName")
        renameFile(oldName, this.newNameInput.value)
    }

    gotoDir(){
        appendDir(this.fileName)
    }

    openMe(){
        openFile(this.fileName)
    }

    deleteMe(){
        deleteFile(this.fileName, this.isDir?1:0)
    }


}
customElements.define('file-item', FileItem);

class FileList extends HTMLElement{
    constructor(fileList, parentDir){
        super()
        this.fileList = fileList
        this.parentDir = parentDir
    }

    connectedCallback(){
        this.appendChild(new FileItem(0,0,0,0,true))

        for(let file of this.fileList){
            this.appendChild(new FileItem(file.name,file.type===1,file.lastModifiedTimeStamp,file.size))
        }
    }


}
customElements.define('file-list', FileList);


class DiskItem extends HTMLElement {
    constructor(diskName, totalBlocks, blocksLeft, isHeader = false) {
        super()
        this.diskName = diskName
        this.totalBlocks = totalBlocks
        this.blocksLeft = blocksLeft
        this.isHeader = isHeader
    }

    connectedCallback() {
        let templateElem = document.getElementById("diskItemTemplate");
        const templateContent = templateElem.content;
        this.appendChild(templateContent.cloneNode(true));
        if (this.isHeader) {
            this.querySelector(".diskName").innerHTML = "空间名"
            this.querySelector(".renameButton").remove()
            return
        }
        this.diskNameDom = this.querySelector(".diskName")
        this.diskVolInfoDom = this.querySelector(".diskVolInfo")
        this.diskVolBarDom = this.querySelector(".diskVolBar")
        this.querySelector(".fileIcon").classList.add("fas","fa-hdd")

        this.diskNameDom.innerHTML = this.diskName
        this.diskVolBarDom.style.width = (100-(this.blocksLeft/this.totalBlocks*100).toFixed(1))+"%"

        this.diskVolInfoDom.innerHTML = genSizeStr((this.totalBlocks-this.blocksLeft)*2048)+"/"+genSizeStr(this.totalBlocks*2048)

        let rb = this.querySelector(".renameButton")
        if (rb) {
            rb.addEventListener("click", evt => this.startRename())
            this.newNameInput = this.querySelector(".newFileNameInput")

        }
        this.diskNameDom.addEventListener("click",evt => this.gotoDisk())
        this.querySelector(".submitRenameBtn").addEventListener("click", evt => this.submitRename())
        this.querySelector(".cancelRenameBtn").addEventListener("click", evt => this.cancelRename())

    }
    startRename(){
        this.classList.add("editingName")
        this.newNameInput.value = this.diskName
        this.newNameInput.select()

    }

    cancelRename(){
        this.classList.remove("editingName")
    }

    submitRename(){
        let oldName = this.diskName
        this.classList.remove("editingName")
        renameFile(oldName, this.newNameInput.value)
    }

    gotoDisk(){
        appendDir(this.diskName)
    }
}
customElements.define('disk-item', DiskItem);

class DiskList extends HTMLElement{
    constructor(diskList){
        super()
        this.diskList = diskList
    }

    connectedCallback(){
        this.appendChild(new DiskItem(0,0,0,true))

        for(let file of this.diskList){
            this.appendChild(new DiskItem(file.name,file.totalBlocks,file.blocksLeft))
        }
    }
}
customElements.define('disk-list', DiskList);