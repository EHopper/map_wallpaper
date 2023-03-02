import os

from PIL import Image
from PIL import ImageEnhance
import rasterio
import rasterio.warp as rwarp

Image.MAX_IMAGE_PIXELS = None

def increase_contrast(im, contrast_scale=3):
    enhancer = ImageEnhance.Contrast(im)
    return enhancer.enhance(contrast_scale)
    
def save_as_jpg(im, save_name, quality=100):
    background = Image.new("RGB", im.size, (255,255,255))
    background.paste(im, mask=im.split()[3]) # 3 is the alpha channel
    background.save(f'{save_name}.jpg', 'JPEG', quality=quality)


def crop_qs_merge_tb(new_filename, merge_filename):
  region = crop_in_1(new_filename)
  region = region.resize((region.width//2, region.height//2))
  fn = get_filename(merge_filename)
  if not fn:
    merged = region
  else:
    merge_to = load(merge_filename)
    merge_to.save('old.tif')
    region = region.resize((merge_to.width, region.height))
    merged = merge_tb_loaded(merge_to, region)
  merged.save(f'{merge_filename}_new.tif')
  return merged

def merge_loaded(im1, im2):
    w = im1.width + im2.width
    # h = max(im1.size[1], im2.size[1])
    h = im1.height
    im2 = im2.resize((im2.width, h))

    im = Image.new("RGBA", (w, h))

    im.paste(im1)
    im.paste(im2, (im1.width, 0))
    return im

def merge(fn1, fn2):
    im1 = load(fn1)
    im2 = load(fn2)

    return merge_loaded(im1, im2)

def merge_tb_loaded(im1, im2):
    w = max(im1.size[0], im2.size[0])
    h = im1.size[1] + im2.size[1]
    im = Image.new("RGBA", (w, h))

    im.paste(im1)
    im.paste(im2, (0, im1.size[1]))

    return im  

def merge_tb(fn1, fn2):
    im1 = load(fn1)
    im2 = load(fn2)
    im = merge_tb_loaded(im1, im2)

    return im

def get_filename(quadrangle_name):
    all_files = os.listdir()
    fn = [fn for fn in all_files if quadrangle_name in fn]
    if not fn: return ''
    return fn[0]

def load(quadrangle_name):
    fn = get_filename(quadrangle_name)
    print('Using {}'.format(fn))
    return Image.open(fn)

START_BOX = (1131, 796, 6219, 7627)

def try_crop(quadrangle_name, start_box=START_BOX):
    im = load(quadrangle_name)
    box = start_box

    input_dict = {'n': 'no', 't': 'top', 'b': 'bottom', 'l': 'left', 'r': 'right'}
    side_mapping = {'t': 1, 'b': 3, 'l': 0, 'r': 2}
    direction_mapping = {'t': 1, 'b': -1, 'l': 1, 'r': -1}
    while True:
        print(box)
        region = im.crop(box)
        region.show()
        side = input('Adjust side? Press n[o], t[op], b[ottom], l[eft], r[ight]:  ')
        if side == 'n':
            region.save('crop_{}_{}_{}_{}_{}.tif'.format(quadrangle_name, box[0], box[1], box[2], box[3]))
            return
        print('Ok, adjusting the {} boundary...'.format(input_dict[side]))        
        amount = input('By how many pixels? (-ve: away from map centre, +ve: towards map centre)  ', )
        b = list(box)
        b[side_mapping[side]] += direction_mapping[side] * int(amount)
        box = tuple(b)
        region.close()

def crop_in_1(quadrangle_name):
    im = load(quadrangle_name)
    box = (0, 0, im.width, im.height)
    side_mapping = {'t': 1, 'b': 3, 'l': 0, 'r': 2}
    direction_mapping = {'t': 1, 'b': -1, 'l': 1, 'r': -1}
    region = im.crop(box)
    region.show()
    crop_adjust = input('Adjust sides? (-ve: away from map centre, +ve: towards map centre) [left, top, right, bottom]', )
    crop_adjust = [int(n) for n in crop_adjust.split(',')]
    print(crop_adjust)
    b = list(box)
    for side, amount in zip(['l', 't', 'r', 'b'], crop_adjust):
        b[side_mapping[side]] += direction_mapping[side] * amount
    box = tuple(b)
    region = im.crop(box)
    region.save('crop_{}_{}_{}_{}_{}.tif'.format(quadrangle_name, box[0], box[1], box[2], box[3]))
    return region
    


def save_quarter_size(filename):
    im = load(filename)
    im = im.resize((im.width//2, im.height//2))
    im.save(f'{filename}_qs.tif')


def transform(quadrangle_name, position='1a'):

    all_files = os.listdir()
    fn = [fn for fn in all_files if quadrangle_name in fn]
    if len(fn) > 1:
        print('More than one file like this!')
        print(fn)
    if len(fn) == 0:
        print('No files like this!')
    fn = fn[0]
    print('Using {}'.format(fn))


    # dst_crs = 'epsg:3857' # This is the google maps projection
    dst_crs = 'epsg:4087' # equirectangular
    src = rasterio.open(fn)
    transform, width, height = rwarp.calculate_default_transform(
        src.crs, dst_crs, src.width, src.height, *src.bounds
        )
    kwargs = src.meta.copy()
    kwargs.update({'crs': dst_crs, 'transform': transform, 'width': width, 'height': height})

    with rasterio.open('{}_{}.tif'.format(quadrangle_name, position), 'w', **kwargs) as dst:
        for i in range(1, src.count + 1):
            rwarp.reproject(
                source=rasterio.band(src, i),
                destination=rasterio.band(dst, i),
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=transform,
                dst_crs=dst_crs,
                resampling=rwarp.Resampling.bilinear)