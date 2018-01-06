#!/usr/bin/env python
#
# deepzoom_multiserver - Example web application for viewing multiple slides
#
# Copyright (c) 2010-2015 Carnegie Mellon University
#
# This library is free software; you can redistribute it and/or modify it
# under the terms of version 2.1 of the GNU Lesser General Public License
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public
# License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#

from collections import OrderedDict
from flask import Flask, abort, make_response, render_template, url_for
from io import BytesIO
import openslide
from openslide import OpenSlide, OpenSlideError
from openslide.deepzoom import DeepZoomGenerator
import os
from optparse import OptionParser
from threading import Lock
from subprocess import call
import xml.etree.ElementTree as ET

SLIDE_DIR = '.'
SLIDE_CACHE_SIZE = 10
DEEPZOOM_FORMAT = 'jpeg'
DEEPZOOM_TILE_SIZE = 512
DEEPZOOM_OVERLAP = 0
DEEPZOOM_LIMIT_BOUNDS = True
DEEPZOOM_TILE_QUALITY = 75
BUCKET = 'gs://dzi-images/'
GCS_URL = 'http://storage.googleapis.com/dzi-images/'
DZIS = './dzis'
DZI = './dzi'

app = Flask(__name__)
app.config.from_object(__name__)
app.config.from_envvar('DEEPZOOM_MULTISERVER_SETTINGS', silent=True)


class PILBytesIO(BytesIO):
    def fileno(self):
        '''Classic PIL doesn't understand io.UnsupportedOperation.'''
        raise AttributeError('Not supported')

class _SlideCache(object):
    def __init__(self, cache_size, dz_opts):
        self.cache_size = cache_size
        self.dz_opts = dz_opts
        self._lock = Lock()
        self._cache = OrderedDict()

    def get(self, barcode):
        with self._lock:
            if barcode in self._cache:
                # Move to end of LRU
                slide = self._cache.pop(barcode)
                self._cache[barcode] = slide
                return slide

#        osr = OpenSlide(path)
#        slide = DeepZoomGenerator(osr, **self.dz_opts)

        if call(['gsutil','cp',app.config['BUCKET']+barcode+'.dzi', app.config['DZI']])==0:
            slide = ET.parse( app.config['DZI'])
        else:
            abort(404)                   

        with self._lock:
            if barcode not in self._cache:
                if len(self._cache) == self.cache_size:
                    self._cache.popitem(last=False)
                self._cache[barcode] = slide
        return slide


'''
class _Directory(object):
    def __init__(self, basedir, relpath=''):
        self.name = os.path.basename(relpath)
        self.children = []
        for name in sorted(os.listdir(os.path.join(basedir, relpath))):
            cur_relpath = os.path.join(relpath, name)
            cur_path = os.path.join(basedir, cur_relpath)
            if os.path.isdir(cur_path):
                cur_dir = _Directory(basedir, cur_relpath)
                if cur_dir.children:
                    self.children.append(cur_dir)
            elif OpenSlide.detect_format(cur_path):
                self.children.append(_SlideFile(cur_relpath))
'''

class _Directory(object):
    def __init__(self, bucket, dzis):
        self.barcodes = []
        with open(dzis,'w') as d:
            if call(['gsutil','ls',bucket+'*.dzi'],stdout=d):
                print("Empty bucket")
                exit
        with open(dzis) as d:
            dzis = d.read().splitlines()
            for dzi in dzis:
                barcode = dzi.partition(app.config['BUCKET'])[2].split('.')[0]
                self.barcodes.append(barcode)

'''
class _SlideFile(object):
    def __init__(self, relpath):
        self.name = os.path.basename(relpath)
        self.url_path = relpath
'''
'''
class _SlideFile(object):
    def __init__(self, gsutil_path):
        self.name = gsutil_path.partition(app.config['BUCKET'])[2].split('.')[0]
        self.url_path = gsutil_path
'''

@app.before_first_request
def _setup():
#    import pdb; pdb.set_trace()
    app.basedir = os.path.abspath(app.config['SLIDE_DIR'])
    config_map = {
        'DEEPZOOM_TILE_SIZE': 'tile_size',
        'DEEPZOOM_OVERLAP': 'overlap',
        'DEEPZOOM_LIMIT_BOUNDS': 'limit_bounds',
    }
    opts = dict((v, app.config[k]) for k, v in config_map.items())
    app.cache = _SlideCache(app.config['SLIDE_CACHE_SIZE'], opts)
    app.directory =_Directory(app.config['BUCKET'],app.config['DZIS'])

'''
def _get_slide(path):
    path = os.path.abspath(os.path.join(app.basedir, path))
    if not path.startswith(app.basedir + os.path.sep):
        # Directory traversal
        abort(404)
    if not os.path.exists(path):
        abort(404)
    try:
        slide = app.cache.get(path)
        slide.filename = os.path.basename(path)
        return slide
    except OpenSlideError:
        abort(404)
'''

def _get_slide(barcode):
    if barcode in app.directory.barcodes:
        try:
            slide = app.cache.get(barcode)
            return slide
        except OpenSlideError:
            abort(404)
    else:
        abort(404)


@app.route('/')
def index():
#    return render_template('files.html', root_dir=_Directory(app.basedir))
#    import pdb; pdb.set_trace()
    return render_template('files.html', root_dir=app.directory)


@app.route('/<barcode>')
def slide(barcode):
#    import pdb; pdb.set_trace()
#    path = 'boxes.tiff'
    slide = _get_slide(barcode)
#    slide = _get_slide('boxes.tiff')
#    slide_url = url_for('dzi', path=path)
#    slide_url = '/boxes.tiff.dzi'
    slide_url = app.config['GCS_URL']+barcode+'_files'
    root = slide.getroot()
    slide_format = root.attrib['Format']
    slide_tilesize = root.attrib['TileSize']
    for child in root:
        if child.tag.find('Size')>=0:
            slide_height = child.attrib['Height']
            slide_width = child.attrib['Width']
        elif child.tag.find('MPP')>=0:
            slide_mpp = child.attrib['mpp']

    return render_template('slide-gcs.html', 
        slide_url=slide_url,
        slide_filename=barcode, 
        slide_mpp=slide_mpp,
        slide_format=slide_format, 
        slide_tilesize=slide_tilesize,
        slide_height=slide_height,
        slide_width=slide_width)

'''
@app.route('/<path:path>.dzi')
def dzi(path):
    import pdb; pdb.set_trace()
    slide = _get_slide(path)
    format = app.config['DEEPZOOM_FORMAT']
    resp = make_response(slide.get_dzi(format))
    resp.mimetype = 'application/xml'
    return resp


@app.route('/<path:path>_files/<int:level>/<int:col>_<int:row>.<format>')
def tile(path, level, col, row, format):
    import pdb; pdb.set_trace()
    slide = _get_slide(path)
    format = format.lower()
    if format != 'jpeg' and format != 'png':
        # Not supported by Deep Zoom
        abort(404)
    try:
        tile = slide.get_tile(level, (col, row))
    except ValueError:
        # Invalid level or coordinates
        abort(404)
    buf = PILBytesIO()
    tile.save(buf, format, quality=app.config['DEEPZOOM_TILE_QUALITY'])
    resp = make_response(buf.getvalue())
    resp.mimetype = 'image/%s' % format
    return resp
'''


if __name__ == '__main__':
    parser = OptionParser(usage='Usage: %prog [options] [slide-directory]')
    parser.add_option('-B', '--ignore-bounds', dest='DEEPZOOM_LIMIT_BOUNDS',
                default=True, action='store_false',
                help='display entire scan area')
    parser.add_option('-c', '--config', metavar='FILE', dest='config',
                help='config file')
#    parser.add_option('-d', '--debug', dest='DEBUG', default=False, action='store_false',
#                help='run in debugging mode (insecure)')
    parser.add_option('-e', '--overlap', metavar='PIXELS',
                dest='DEEPZOOM_OVERLAP', type='int',
                help='overlap of adjacent tiles [1]')
    parser.add_option('-f', '--format', metavar='{jpeg|png}',
                dest='DEEPZOOM_FORMAT',
                help='image format for tiles [jpeg]')
    parser.add_option('-l', '--listen', metavar='ADDRESS', dest='host',
                default='127.0.0.1',
                help='address to listen on [127.0.0.1]')
    parser.add_option('-p', '--port', metavar='PORT', dest='port',
                type='int', default=5000,
                help='port to listen on [5000]')
    parser.add_option('-Q', '--quality', metavar='QUALITY',
                dest='DEEPZOOM_TILE_QUALITY', type='int',
                help='JPEG compression quality [75]')
    parser.add_option('-s', '--size', metavar='PIXELS',
                dest='DEEPZOOM_TILE_SIZE', type='int',
                help='tile size [254]')

#    import pdb; pdb.set_trace()
    (opts, args) = parser.parse_args()
    # Load config file if specified
    if opts.config is not None:
        app.config.from_pyfile(opts.config)
    # Overwrite only those settings specified on the command line
    for k in dir(opts):
        if not k.startswith('_') and getattr(opts, k) is None:
            delattr(opts, k)
    app.config.from_object(opts)
    # Set slide directory
    try:
        app.config['SLIDE_DIR'] = args[0]
    except IndexError:
        pass

#    app.debug = True
    app.run(host=opts.host, port=opts.port, threaded=True)
