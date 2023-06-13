import json
import math

from flask import Flask, request, send_file, jsonify
import os
from manager import StorageManager

app = Flask(__name__, static_url_path="")


@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    file_path = f'./files/{filename}.zip'
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        return f'File {filename}.zip not found', 404


@app.route('/gotoDir', methods=['POST'])
def goto_directory():
    data = request.get_json()
    directory = data.get('directory')
    if directory:
        os.chdir(directory)
        return f'Changed current directory to {directory}'
    else:
        return 'No directory provided', 400


@app.route('/rename', methods=['POST'])
def rename_file():
    data = request.get_json()
    old_name = data.get('old_name')
    new_name = data.get('new_name')
    if old_name and new_name:
        try:
            os.rename(old_name, new_name)
            return f'Renamed file {old_name} to {new_name}'
        except OSError as e:
            return f'Failed to rename file: {str(e)}', 500
    else:
        return 'Invalid request data', 400


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
    size: float = data.get("size")  # 磁盘大小多少M
    dataBlockCount = math.ceil(size * 64) * 8
    inodeCount = math.ceil(size * 4) * 8
    storageMgr.createDisk(dataBlockCount, inodeCount, data.get("diskName"))
    ans = storageMgr.getDiskReport()
    return genResponse(ans)


@app.route('/disk_report')
def disk_report():
    data = storageMgr.getDiskReport()
    return genResponse(data)


@app.route('/update_file_list')
def get_files():
    data = {
        "nowDir": storageMgr.getDir(),
        "files": storageMgr.getFileList()
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
