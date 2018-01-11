#!/usr/bin/env python

from __future__ import print_function
import random
import os
import deepzoom_tile
from subprocess import call
from optparse import OptionParser
import shutil

def get_slides(slidelist):
    with open(slidelist) as f:
        slides = f.read().splitlines()
#        random.shuffle(slides)
        return slides

def run(opts,args,slidelist):
    slides = get_slides(slidelist)
#    import pdb; pdb.set_trace()
    for slide in slides:
        if slide[0] == '#':
            print("Skipping {}\n".format(slide))
            continue
        else:
            
            print ("{}\n".format(slide))
        basename = slide.partition('Diagnostic_image/')[2].partition('.svs')[0]
        slidepath = './' + basename + '.svs'
        if call(['gsutil','cp',slide, slidepath])==0:
            call(['ls', '-l', slidepath])
            deepzoom_tile.DeepZoomStaticTiler(slidepath, basename, opts.format,
                opts.tile_size, opts.overlap, opts.limit_bounds, opts.quality,
                opts.workers, opts.with_viewer).run()
            call(['du', '-s', basename+'_files'])
#           if not opts.dev:
            if True:
                call(['gsutil','-m', '-q', 'cp', '-a','public-read', basename +'.dzi', 'gs://dzi-images/' + basename + '.dzi'])
                call(['gsutil','-m', '-q', 'cp', '-a','public-read','-r', basename+'_files', 'gs://dzi-images/' + basename + '_files'])
                shutil.rmtree('./' + basename.partition('/')[0])
           
if __name__ == '__main__':
    parser = OptionParser(usage='Usage: %prog [options] <slide>')
    parser.add_option('-B', '--ignore-bounds', dest='limit_bounds',
                default=True, action='store_false',
                help='display entire scan area')
    parser.add_option('-e', '--overlap', metavar='PIXELS', dest='overlap',
                type='int', default=0,
                      help='overlap of adjacent tiles [0]')
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
                help='tile size [512]')
    parser.add_option('-d', '--dev', metavar='DEV', dest='dev',
                default=False, action='store_true',
                help='use short svs file list')

    (opts, args) = parser.parse_args()

    if opts.dev:
        slidelist = './dev_images.txt'
    else:
        slidelist = './diagnostic_images.txt'                      
    run(opts,args,slidelist)
