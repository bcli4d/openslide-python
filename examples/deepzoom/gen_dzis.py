#!/usr/bin/env python

import random
import os
import deepzoom_tile
from subprocess import call
from optparse import OptionParser
import shutil

def get_slides(slidelist):
    with open(slidelist) as f:
        slides = f.read().splitlines()
        random.shuffle(slides)
        return slides

def run(opts,args,slidelist):
    import pdb; pdb.set_trace()
    slidepath = './temp.svs'
    slides = get_slides(slidelist)
    for slide in slides:
        print slide
        if call(['gsutil','cp',slide, slidepath])==0:
            basename = slide.rsplit('/',1)[1].split('.',1)[0]
            deepzoom_tile.DeepZoomStaticTiler(slidepath, basename, opts.format,
                opts.tile_size, opts.overlap, opts.limit_bounds, opts.quality,
                opts.workers, opts.with_viewer).run()
            call(['gsutil','-m','cp', '-a','public-read', basename+'.dzi', 'gs://dzi-images'])
            call(['gsutil','-m','cp', '-a','public-read','-r', basename+'_files', 'gs://dzi-images'])
            os.remove(basename+'.dzi')
            shutil.rmtree(basename+'_files')
           
if __name__ == '__main__':
    parser = OptionParser(usage='Usage: %prog [options] <slide>')
    parser.add_option('-B', '--ignore-bounds', dest='limit_bounds',
                default=True, action='store_false',
                help='display entire scan area')
    parser.add_option('-e', '--overlap', metavar='PIXELS', dest='overlap',
                type='int', default=0,
                help='overlap of adjacent tiles [1]')
    parser.add_option('-f', '--format', metavar='{jpeg|png}', dest='format',
                default='jpeg',
                help='image format for tiles [jpeg]')
    parser.add_option('-j', '--jobs', metavar='COUNT', dest='workers',
                type='int', default=4,
                help='number of worker processes to start [4]')
    parser.add_option('-o', '--output', metavar='NAME', dest='basename',
                help='base name of output file')
    parser.add_option('-Q', '--quality', metavar='QUALITY', dest='quality',
                type='int', default=90,
                help='JPEG compression quality [90]')
    parser.add_option('-r', '--viewer', dest='with_viewer',
                action='store_true',
                help='generate directory tree with HTML viewer')
    parser.add_option('-s', '--size', metavar='PIXELS', dest='tile_size',
                type='int', default=512,
                help='tile size [254]')

    (opts, args) = parser.parse_args()

    '''
    try:
        slidepath = args[0]
    except IndexError:
        parser.error('Missing slide argument')
    if opts.basename is None:
        opts.basename = os.path.splitext(os.path.basename(slidepath))[0]
    '''


    os.environ["PYTHONPATH"] = "/home/bcliffor/git-home/openslide-python/openslide"
    slidelist = '/home/bcliffor/projects/dzis/diagnostic_images.txt'                      
    run(opts,args,slidelist)
