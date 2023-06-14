import json
import math

from flask import Flask, request, send_file, jsonify
import os
from manager import StorageManager
import time

app = Flask(__name__, static_url_path="")


@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    file_path = f'./files/{filename}.zip'
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        return f'File {filename}.zip not found', 404


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


@app.route('/remove', methods=['POST'])
def remove_file():
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


def genResponse(data, success=True, msg=""):
    return jsonify({
        "success": success,
        "msg": msg,
        "data": data
    })


if __name__ == '__main__':
    storageMgr = StorageManager()
    app.run()
