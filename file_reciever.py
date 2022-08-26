import os.path

from flask import Flask, request
import requests


app = Flask(__name__)


@app.route('/write/<string:name>', methods=('PUT', ))
def write(name: str):
    # read body, write to file
    file_parts = name.split('.')
    file_name = file_parts[0]
    file_ext = '.'.join(['']+file_parts[1:])
    content = request.get_data()
    fid = 0
    fp = f'{file_name}_{fid}{file_ext}'
    found = os.path.exists(fp)
    while found:
        fid += 1
        fp = f'{file_name}_{fid}{file_ext}'
        found = os.path.exists(fp)
    with open(fp, 'wb') as f:
        f.write(content)
    requests.post('https://discord.com/api/webhooks/1011285082935398411/tVk7RaQId68gOgj7bePHQ-u5sX2nqlJX5zoa6InsZk-j0p5cct3KOblvSd77aPbM1Wzl',
                  json={'content': f'{fp} written, {len(content)} bytes'})
    return f'Created {fp}', 201


@app.route('/')
def idx():
    return 'api: PUT /write/&ltfilename&gt'


app.run(host='0.0.0.0', port=8888)
