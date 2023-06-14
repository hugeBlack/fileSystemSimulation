import json
import math
from hbdisk import HbDisk
from flask import Flask, request, send_file, jsonify, redirect
import os
from manager import StorageManager, DiskManager

app = Flask(__name__, static_url_path="")


@app.route('/download/<path:filename>', methods=['GET'])
def download_file(filename):
    try:
        fileBytes = storageMgr.downloadFile(filename)
        return send_file(fileBytes, as_attachment=True, download_name=filename.split("/")[-1])
    except Exception as e:
        return genResponse("", False, e.args[0])


@app.route('/goto', methods=['POST'])
def goto_directory():
    data = request.get_json()
    directory = data.get('directory')
    try:
        if len(directory) == 0:
            storageMgr.clearDisk()
        else:
            storageMgr.switchDisk(directory[0])
            storageMgr.switchDir(directory[1:])
        return get_files()
    except Exception as e:
        return genResponse("", False, e.args[0])


@app.route('/rename', methods=['POST'])
def rename_file():
    data = request.get_json()
    oldName = data.get('oldName')
    newName = data.get('newName')
    try:
        storageMgr.renameFile(oldName, newName)
        return get_files()
    except Exception as e:
        return genResponse("", False, e.args[0])


@app.route('/delete', methods=['POST'])
def delete_file():
    data = request.get_json()
    fileName = data.get('fileName')
    fileType = data.get("fileType")
    try:
        if fileType == 1:
            storageMgr.deleteFolder(fileName)
        else:
            storageMgr.deleteFile(fileName)
        return get_files()
    except Exception as e:
        return genResponse("", False, e.args[0])


@app.route('/create_disk', methods=['POST'])
def create_disk():
    data = request.get_json()
    try:
        size: float = data.get("size")  # 磁盘大小多少M
        dataBlockCount = math.ceil(size * 64) * 8
        inodeCount = math.ceil(size * 4) * 8
        storageMgr.createDisk(dataBlockCount, inodeCount, data.get("diskName"))
        return get_files()
    except Exception as e:
        return genResponse("", False, e.args[0])


@app.route('/create_file', methods=['POST'])
def create_file():
    data = request.get_json()
    try:
        fileName: str = data.get("fileName")
        storageMgr.createFile(fileName)
        return get_files()
    except Exception as e:
        return genResponse("", False, e.args[0])


@app.route('/create_folder', methods=['POST'])
def create_folder():
    data = request.get_json()
    try:
        fileName: str = data.get("folderName")
        storageMgr.createFolder(fileName)
        return get_files()
    except Exception as e:
        return genResponse("", False, e.args[0])


@app.route('/update_file_list')
def get_files():
    dirs = storageMgr.getDir()
    if len(dirs) > 0:
        data = {
            "nowDir": dirs,
            "files": storageMgr.getFileList()
        }
    else:
        data = {
            "nowDir": dirs,
            "disks": storageMgr.getDiskReport()
        }
    return genResponse(data)


@app.route('/open_file', methods=['POST'])
def open_file():
    data = request.get_json()
    try:
        fileName: str = data.get("fileName")
        filePath = storageMgr.openFile(fileName)
        return genResponse({
            "filePath": filePath
        })
    except Exception as e:
        return genResponse("", False, e.args[0])


@app.route('/close_file', methods=['POST'])
def close_file():
    data = request.get_json()
    try:
        filePath: str = data.get("filePath")
        storageMgr.closeFile(filePath)
        return genResponse('')
    except Exception as e:
        return genResponse("", False, e.args[0])


def genResponse(data, success=True, msg=""):
    return jsonify({
        "success": success,
        "msg": msg,
        "data": data
    })


@app.route("/read_all", methods=['POST'])
def read_all():
    data = request.get_json()
    try:
        filePath: str = data.get("filePath")
        content = storageMgr.readAll(filePath)
        return genResponse({
            "content": content
        })
    except Exception as e:
        return genResponse("", False, e.args[0])


@app.route("/write_from_start", methods=['POST'])
def write_from_start():
    data = request.get_json()
    try:
        filePath: str = data.get("filePath")
        content = data.get("content")
        storageMgr.writeFromStart(filePath, content)
        content = storageMgr.readAll(filePath)
        return genResponse({
            "content": content
        })
    except Exception as e:
        return genResponse("", False, e.args[0])


@app.route("/upload", methods=['POST'])
def upload():
    if 'file' not in request.files:
        return genResponse("", False, "No file uploaded!")
    file = request.files['file']
    if file.filename == '':
        return genResponse("", False, "No file uploaded!")
    try:
        storageMgr.uploadNewFile(file.stream, file.filename)
        return get_files()
    except Exception as e:
        return genResponse("", False, e.args[0])


@app.route("/powerOff", methods=['POST'])
def powerOff():
    try:
        storageMgr.powerOff()
        return genResponse("")
    except Exception as e:
        return genResponse("", False, e.args[0])


@app.route("/")
def main():
    return redirect("./dirview.html", code=302)


if __name__ == '__main__':
    # 加载所有hbdk空间文件
    dmList = []

    for f in os.listdir('.'):
        if f.endswith('.hbdk'):
            file_stats = os.stat(f)
            file_size = file_stats.st_size
            hbdk_file = open(f, "rb+")
            disk = HbDisk(fileSize=file_size, reader=hbdk_file)
            dm = DiskManager(disk)
            dmList.append(dm)

    storageMgr = StorageManager(dmList)
    app.run()
