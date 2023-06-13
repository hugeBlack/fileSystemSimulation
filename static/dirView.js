aa = document.getElementById("navBarHolder")



fw = document.getElementById("fileListHolder")
fetch(
    "/update_file_list"

).then( async response =>{
    let f = await response.json()
    console.log(f)
    let d=  new DirBar(f.nowDir)
    aa.appendChild(d)
    fw.appendChild(new FileList(f.files,"/test"))
    }
    
)


