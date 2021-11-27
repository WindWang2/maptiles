'''
This code is used to generate tif image  from bounding boxes (Lat long)

Some part of code reference from https://github.com/zhengjie9510/google-map-downloader.
@date: 2021-11-15
@author: WindWang2
'''
import math
from osgeo import gdal
from typing import Tuple
import numpy as np
import itertools

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


class Downloader(Thread):
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


# lt: left top, rb: right bottom
def main(lt_lon: float, lt_lat: float, rb_lon: float, rb_lat: float,
         zoom_level: int, out_file_path: str):
    assert (zoom_level < 20 and zoom_level > 0)
    res = proj_ex / (2**zoom_level)
    lt_x, lt_y = wgs_to_mercaotr(lt_lon, lt_lat)
    rb_x, rb_y = wgs_to_mercaotr(rb_lon, rb_lat)

    lt_tile_x, lt_tile_y = xy_to_tilexy(lt_x, lt_y, zoom_level)
    rb_tile_x, rb_tile_y = xy_to_tilexy(rb_x, rb_y, zoom_level)

    img_width = abs(rb_tile_x - lt_tile_x)
    img_height = abs(rb_tile_y - lt_tile_y)

    tile_x_list = np.arange(lt_tile_x, rb_tile_x + 1, 1)
    tile_y_list = np.arange(rb_tile_y, lt_tile_y + 1, 1)

    tile_list = []
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
            img_left[0] = math.floor(abs(tile_x - lt_tile_x)) * 256
            img_right[0] = img_left[0] + 256
        else:
            tile_left[0] = 0
            tile_right[0] = math.floor(abs(rb_tile_x - tile_x - 1) * 256)
            img_left[0] = math.floor(img_width * 256) - tile_right[0]
            img_right[0] = math.floor(img_width * 256)

        # from bottom to top
        if tile_y < rb_tile_y:
            tile_left[1] = 0
            tile_right[1] = math.floor(abs(tile_y + 1 - rb_tile_y) * 256)
            img_left[1] = math.floor(abs(lt_tile_y - tile_y - 1) * 256)
            img_right[1] = math.floor(img_height * 256)
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

        tile_list.append(
            (tile_x, tile_y, tile_left, tile_right, img_left, img_right))

    print(tile_list)


if __name__ == '__main__':
    print(wgs_to_mercaotr(120.23770568, 23.83216986))
    # TMS
    # print(wgs_to_tilexy(120.23770568, 23.8321698, 19))
    # Google
    # print(wgs_to_tilexy(120.23770568, 23.8321698, 19, is_topleft_origin=True))
    # test
    main(120.23770568, 23.8321698, 120.23870568, 23.8311698, 19, 'tste')
