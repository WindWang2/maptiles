'''
This code is used to generate tif image  from bounding boxes (Lat long)

Some part of code reference from https://github.com/zhengjie9510/google-map-downloader.
@date: 2021-11-15
@author: WindWang2
'''
import math
from osgeo import gdal, osr
from typing import Tuple
import numpy as np
import itertools
import multiprocessing
import threading
from threading import Thread
import sqlite3

# define some constants of the maps
# ----------------------------------------------------------------
max_lat = 85.0511287798
# Spherical Mercator extent (-20037508.34, -20037508.34, 20037508.34, 20037508.34)
# which means the centor point is (0, 0)
proj_ex = 20037508.3427892439067364
tile_pixels = 256
# ----------------------------------------------------------------


def wgs_to_mercaotr(lon: float, lat: float) -> Tuple[float, float]:
    lat = max_lat if lat > max_lat else lat
    lat = -max_lat if lat < -max_lat else lat
    x = lon * proj_ex / 180
    y = math.log(math.tan((90 + lat) * math.pi / 360)) / (math.pi / 180)
    y = y * proj_ex / 180
    return x, y


# Web Mercator to WGS-84
def mercator_to_wgs(x: float, y: float) -> Tuple[float, float]:
    x2 = x / proj_ex * 180
    y2 = y / proj_ex * 180
    y2 = 180 / math.pi * (2 * math.atan(math.exp(y2 * math.pi / 180)) -
                          math.pi / 2)
    return x2, y2

# tile xy to Mercator xy
def tilexy_to_xy(x: float, y: float, zoom_level: int, is_topleft_origin: bool = False):
    assert (zoom_level < 20 and zoom_level > 0)
    num = 2 ** (zoom_level)
    tx = ((x / num) * 2 - 1) * proj_ex
    ty = ((y / num) * 2 - 1) * proj_ex
    if is_topleft_origin:
        ty = ((1 - y / num) * 2 - 1) * proj_ex

    # print('mercator', tx, ty)
    return tx, ty


def xy_to_tilexy(x: float,
                 y: float,
                 zoom_level: int,
                 is_topleft_origin: bool = False):
    # x, y = wgs_to_mercaotr(lon, lat)
    x /= proj_ex
    y /= proj_ex
    num = 2**(zoom_level)
    x = (x + 1) / 2
    y = (y + 1) / 2
    assert (zoom_level < 20 and zoom_level > 0)
    if is_topleft_origin:
        y = (1 - y)
    # tile_x = math.floor(x * num)
    tile_x = x * num
    # tile_y = math.floor(y * num)
    tile_y = y * num

    return tile_x, tile_y


class Downloader_Thread(Thread):
    # multiple threads downloader
    def __init__(self, index, count, urls, datas):
        # index represents the number of threads
        # count represents the total number of threads
        # urls represents the list of URLs nedd to be downloaded
        # datas represents the list of data need to be returned.
        super().__init__()
        self.urls = urls
        self.datas = datas
        self.index = index
        self.count = count

    def download(self, url):
        HEADERS = {
            'User-Agent':
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36 Edg/88.0.705.68'
        }
        header = ur.Request(url, headers=HEADERS)
        err = 0
        while (err < 3):
            try:
                data = ur.urlopen(header).read()
            except:
                err += 1
            else:
                return data
        raise Exception("Bad network link.")

    def run(self):
        for i, url in enumerate(self.urls):
            if i % self.count != self.index:
                continue
            self.datas[i] = self.download(url)


def generate_image(out_file_path: str):
    pass


# sqlite_mutex = threading.Lock()
# All the data are not the same, so we do not use lock.


class Dump_tiles_Thread(Thread):
    def __init__(self, mbtfile_path, tile_list, start_id, end_id):
        super().__init__()
        self.mbtfile_path = mbtfile_path
        self.start_id = start_id
        self.end_id = end_id
        self.tile_list = tile_list

    def dump_tile(self, cons, idx, idy, zoom_level):
        q_str = "SELECT * FROM tiles WHERE zoom_level={} and tile_column={} and tile_row={}".format(
            zoom_level, idx, idy)
        # print(q_str)
        re = cons.execute(q_str)
        out = re.fetchall()
        if len(out) == 0:
            return []
        else:
            return out[0][3]

    def run(self):
        # with sqlite_mutex:
        # if not run normal, add check_same_thread = False;
        cons = sqlite3.connect(self.mbtfile_path)
        for i in range(self.start_id, self.end_id):
            idx = self.tile_list[i]['tx']
            idy = self.tile_list[i]['ty']
            zoom_level = self.tile_list[i]['z']
            self.tile_list[i]['img_data'] = self.dump_tile(
                cons, idx, idy, zoom_level)

        cons.commit()
        cons.close()


# lt: left top, rb: right bottom
def main(lt_lon: float, lt_lat: float, rb_lon: float, rb_lat: float,
         zoom_level: int, out_file_path: str):

    assert (zoom_level < 20 and zoom_level > 0)
    res = proj_ex / (2**zoom_level)
    lt_x, lt_y = wgs_to_mercaotr(lt_lon, lt_lat)
    rb_x, rb_y = wgs_to_mercaotr(rb_lon, rb_lat)

    lt_tile_x, lt_tile_y = xy_to_tilexy(lt_x, lt_y, zoom_level)
    rb_tile_x, rb_tile_y = xy_to_tilexy(rb_x, rb_y, zoom_level)

    fixToPixel = lambda x: math.floor((x - math.floor(x)) * 256) * 1/256 + math.floor(x)
    print('fix_before', lt_tile_x, lt_tile_y ,rb_tile_x, rb_tile_y)
    lt_tile_x = fixToPixel(lt_tile_x)
    lt_tile_y = fixToPixel(lt_tile_y)
    rb_tile_x = fixToPixel(rb_tile_x)
    rb_tile_y = fixToPixel(rb_tile_y)
    print('fix_after', lt_tile_x, lt_tile_y ,rb_tile_x, rb_tile_y)

    f_lt_lon, f_lt_lat =  mercator_to_wgs(*tilexy_to_xy(lt_tile_x, lt_tile_y, zoom_level))
    f_rb_lon, f_rb_lat =  mercator_to_wgs(*tilexy_to_xy(rb_tile_x, rb_tile_y, zoom_level))
    print(lt_lon, lt_lat, f_lt_lon, f_lt_lat)
    print(rb_lon, rb_lat,f_rb_lon, f_rb_lat)

    img_width = abs(rb_tile_x - lt_tile_x) * 256
    img_height = abs(rb_tile_y - lt_tile_y) * 256
    print('height', 'width', img_height, img_width)

    tile_x_list = np.arange(math.floor(lt_tile_x), rb_tile_x, 1)
    # print(tile_x_list, rb_tile_x)
    # print(rb_tile_x)
    tile_y_list = np.arange(math.floor(rb_tile_y), lt_tile_y, 1)

    tile_list = []
    # TODO: deal the google tiles (with is_topleft_origin is True)
    for ix, iy in itertools.product(tile_x_list, tile_y_list):
        tile_x, tile_y = math.floor(ix), math.floor(iy)

        # in tile png image coordinates (pixels)
        tile_left = [0, 0]
        tile_right = [256, 256]
        img_left = [0, 0]
        img_right = [img_width, img_height]
        if tile_x < lt_tile_x:
            tile_left[0] = math.floor(abs(lt_tile_x - tile_x) * 256)
            tile_right[0] = 256
            img_left[0] = 0
            img_right[0] = 256 - tile_left[0]
        elif tile_x + 1 < rb_tile_x:
            tile_left[0] = 0
            tile_right[0] = 256
            img_left[0] = math.floor(abs(tile_x - lt_tile_x) * 256)
            img_right[0] = img_left[0] + 256
        else:
            # print(tile_x, rb_tile_x, lt_tile_x)
            tile_left[0] = 0
            tile_right[0] = math.floor(abs(rb_tile_x - tile_x) * 256)
            img_left[0] = math.floor(img_width) - tile_right[0]
            img_right[0] = math.floor(img_width)
            # print(tile_left[0], tile_right[0], img_left[0], img_right[0])
        # from bottom to top
        print(tile_y, rb_tile_y, lt_tile_y)
        if tile_y < rb_tile_y:
            tile_left[1] = 0
            tile_right[1] = math.floor(abs(tile_y + 1 - rb_tile_y) * 256)
            img_left[1] = math.floor(abs(img_height)) - tile_right[1]
            img_right[1] = math.floor(img_height)
        elif tile_y + 1 < lt_tile_y:
            tile_left[1] = 0
            tile_right[1] = 256
            img_left[1] = math.floor(abs(tile_y + 1 - lt_tile_y) * 256)
            img_right[1] = img_left[1] + 256
        else:
            tile_left[1] = math.floor(abs(lt_tile_y - tile_y - 1) * 256)
            tile_right[1] = 256
            img_left[1] = 0
            img_right[1] = 256 - tile_left[1]
            print(img_left[1])
        # print(tile_left, tile_right, img_left, img_right)
        tile_list.append({
            'tx': tile_x,
            'ty': tile_y,
            'z': zoom_level,
            'tl': tile_left,
            'tr': tile_right,
            'iml': img_left,
            'imr': img_right,
            'img_data': []
        })
    print(len(tile_list))
    [print(i) for i in tile_list]
    tasks = [
        Dump_tiles_Thread('../../Downloads/test_sample.mbtiles', tile_list, 0,
                          5),
        Dump_tiles_Thread('../../Downloads/test_sample.mbtiles', tile_list, 5,
                          9)
    ]
    for i in tasks:
        i.start()
    for i in tasks:
        i.join()
    # print(tile_list)
    extent = {}
    extent['LT'] = (f_lt_lon, f_lt_lat)
    extent['RB'] = (f_rb_lon, f_rb_lat)
    gt = (extent['LT'][0], (extent['RB'][0] - extent['LT'][0]) / math.floor(img_width), 0,
          extent['LT'][1], 0, (extent['RB'][1] - extent['LT'][1]) / math.floor(img_height))
    print(extent)
    print('gt', gt)
    driver = gdal.GetDriverByName('GTiff')
    ds = driver.Create('../xxx.tif', math.floor(img_width),
                       math.floor(img_height), 3, gdal.GDT_Byte)
    data = np.zeros((3, math.floor(img_height), math.floor(img_width)),
                    dtype=np.uint8)
    ds.SetGeoTransform(gt)
    proj = osr.SpatialReference()
    proj.ImportFromEPSG(4326)
    ds.SetSpatialRef(proj)

    for idx, itile in enumerate(tile_list):
        if itile['img_data'] == []:
            print(itile)
            continue
        tile_mem = gdal.FileFromMemBuffer('/vsimem/test.jpg',
                                          itile['img_data'])
        tile_ds = gdal.OpenEx('/vsimem/test.jpg')
        tile_data = tile_ds.ReadAsArray()
        # print(tile_data.shape)
        # print(data.shape)
        dxs = itile['iml'][1]
        dxe = itile['imr'][1]
        dys = itile['iml'][0]
        dye = itile['imr'][0]
        ixs = itile['tl'][1]
        ixe = itile['tr'][1]
        iys = itile['tl'][0]
        iye = itile['tr'][0]

        data[:, dxs:dxe, dys:dye] = tile_data[:, ixs:ixe, iys:iye]

    for i in range(3):
        ds.GetRasterBand(i + 1).WriteArray(data[i, :, :])

    print(len(tile_list))


if __name__ == '__main__':
    # print(wgs_to_mercaotr(120.23770568, 23.83216986))
    # TMS
    # print(wgs_to_tilexy(120.23770568, 23.8321698, 19))
    # Google
    # print(
    #     xy_to_tilexy(*wgs_to_mercaotr(120.459268, 23.596711),
    #                  19,
    #                  is_topleft_origin=True))
    # test
    main(120.4524480, 23.601130, 120.45368, 23.59995, 19, 'tste')
    # main(120.43629,23.60542,120.45643,23.59085,19,'ttt')
