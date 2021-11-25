'''
This code is used to generate tif image  from bounding boxes (Lat long)

Some part of code reference from https://github.com/zhengjie9510/google-map-downloader.
@date: 2021-11-15
@author: WindWang2
'''
import math
from osgeo import gdal
from typing import Tuple

# define some constants of the maps
# ----------------------------------------------------------------
max_lat = 85.0511287798
# Spherical Mercator extent (-20037508.34, -20037508.34, 20037508.34, 20037508.34)
# which means the centor point is (0, 0)
proj_ex = 20037508.3427892439067364
# ----------------------------------------------------------------

def wgs_to_mercaotr(lng:float, lat:float) -> Tuple[float, float]:
    lat = max_lat if lat > max_lat else lat
    lat = -max_lat if lat < -max_lat else lat
    x = lng * proj_ex / 180
    y = math.log(math.tan((90 + lat) * math.pi / 360)) / (math.pi / 180)
    y = y * proj_ex / 180
    return x, y

def wgs_to_tilexy(lng:float,
                  lat:float,
                  zoom_level:int,
                  is_topleft_origin:bool=False):
    x, y = wgs_to_mercaotr(lng, lat)
    x /= proj_ex
    y /= proj_ex
    num = 2**(zoom_level)
    x = (x + 1) / 2
    y = (y + 1) / 2
    assert(zoom_level < 20  and zoom_level > 0)
    if is_topleft_origin:
        y = (1 - y) / 2

    tile_x = math.floor(x*num)
    tile_y = math.floor(y*num)
    return tile_x, tile_y

if __name__ == '__main__':
    print(wgs_to_mercaotr(120.23770568,23.83216986))
    # TMS
    print(wgs_to_tilexy(120.23770568, 23.8321698, 19))
    # Google
    print(wgs_to_tilexy(120.23770568, 23.8321698, 19, is_topleft_origin=True))
