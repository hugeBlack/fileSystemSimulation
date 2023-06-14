const urlParams = new URLSearchParams(window.location.search);
const filePath = urlParams.get('path');
const fileInputDom = document.querySelector("#fileHolder>textarea")
const pathDom = document.querySelector("#filePath")
const textFileViewerDom = document.querySelector("#textFileViewer")

function readFile(){
    textFileViewerDom.classList.remove("opened")
    fetch(
        "/read_all",{
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                    "filePath":filePath
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
            fileInputDom.value = f.data.content
            textFileViewerDom.classList.add("opened")
    }
    )
}

function writeFile(){
    let content = fileInputDom.value
    fetch(
        "/write_from_start",{
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                    "filePath":filePath,
                    "content": content
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
            fileInputDom.value = f.data.content
    }
    )
}

let closed = false
function closeFile(){
    if(closed) return true
    closed = true
    fetch(
        "/close_file",{
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                    "filePath":filePath,
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
        window.close()
        }
    )
    return false
}

function download(){
    window.open("/download/"+filePath)
}

function prepareUI(){
    pathDom.innerHTML = filePath
}
prepareUI()
