class DirItem extends HTMLElement{
    constructor(lastDir,dir,isLast,isRoot = false){
        super()
        this.dirStr = dir
        this.isLast = isLast
        this.lastDir = lastDir
        this.isRoot = isRoot
    }

    connectedCallback(){
        if(this.isLast){
            this.contentDom = document.createElement("span")
        }else{
            this.contentDom = document.createElement("a")
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

}
customElements.define('dir-item', DirItem);

class DirBar extends HTMLElement{
    constructor(dirList){
        super()
        this.dirList = dirList
    }

    connectedCallback(){
        let count = this.dirList.length
        let nowPath = ""
        let homeBtn = new DirItem("/", nowPath,false,true)
        this.appendChild(homeBtn)
        for(let i = 0;i<count;i++){
            nowPath += ("/"+ this.dirList[i])
            let a = new DirItem(this.dirList[i], nowPath,i===count-1)
            this.appendChild(a)
        }
    }


}
customElements.define('dir-bar', DirBar);


function TimestampToDate(Timestamp) {
    let date1 = new Date(Timestamp);
    return date1.toLocaleDateString().replace(/\//g, "-") + " " + date1.toTimeString().substr(0, 8);
}
class FileItem extends HTMLElement{
    constructor(fileName,isDir,lastModifiedTimestamp,size,path,isHeader = false){
        super()
        this.fileName = fileName
        this.isDir = isDir
        this.lastModifiedTimestamp = lastModifiedTimestamp
        this.size = size
        this.path = path
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
            this.querySelector(".downloadButton").remove()
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
            this.querySelector(".downloadButton").remove()
        }else{
            this.querySelector(".fileIcon").classList.add("fas","fa-file")
            if(this.size > 1073741824){
                this.fileSizeDom.innerHTML = (this.size/1073741824).toFixed(2) + "GiB"
            }else if (this.size > 1048576){
                this.fileSizeDom.innerHTML = (this.size/1048576).toFixed(2) + "MiB"
            }else if (this.size > 1024){
                this.fileSizeDom.innerHTML = (this.size/1024).toFixed(2) + "KiB"
            }else{
                this.fileSizeDom.innerHTML = this.size + "B"
            }
        }
        if(this.fileName!=="..."){
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

        this.fileName = this.newNameInput.value
        this.fileNameDom.innerHTML = this.fileName
        let a = this.path.split("/")
        a[a.length-1] = this.fileName
        this.path = a.join("/")
        this.classList.remove("editingName")
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
        this.appendChild(new FileItem(0,0,0,0,0,true))
        if(this.parentDir){
            this.appendChild(new FileItem("...",1,0,0,this.parentDir))
        }

        for(let file of this.fileList){
            this.appendChild(new FileItem(file.name,file.isDir,file.lastModifiedTimeStamp,file.size,file.path))
        }
    }


}
customElements.define('file-list', FileList);