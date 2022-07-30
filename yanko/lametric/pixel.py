import cv2
import numpy as np
from multiprocessing.pool import ThreadPool
from base64 import b64encode

PADDING = 200
GRID_LINES = True


def makePixelate(img, output_img, imheight, imwidth, width, height, block_size):
    for i in range(0, imheight // block_size):
        for j in range(0, imwidth // block_size):

            x, x2 = j * width, (j + 1) * width
            y, y2 = i * height, (i + 1) * height

            a = img[y:y2, x:x2]
            a = np.array(a)

            mean_color = np.mean(a, axis=(0, 1))
            mean_color = tuple([int(mean_color[0]), int(
                mean_color[1]), int(mean_color[2])])

            if GRID_LINES:
                a = np.ones((height-2, width-2, 3), np.uint8)*mean_color
                a = cv2.copyMakeBorder(
                    a, 1, 1, 1, 1, borderType=cv2.BORDER_CONSTANT, value=0)
            else:
                a = np.ones((height, width, 3), np.uint8)*mean_color

            output_img[y:y2, x:x2] = a

    lab = cv2.cvtColor(output_img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=1.0, tileGridSize=(8, 8))
    cl = clahe.apply(l)
    limg = cv2.merge((cl, a, b))
    output_img = cv2.cvtColor(cv2.resize(limg, (8, 8)), cv2.COLOR_LAB2BGR)
    base64_str = cv2.imencode('.png', output_img)[1].tostring()
    base64_str = b64encode(base64_str)
    return f"data:image/png;base64,{base64_str.decode()}"


def pixelate(img, block_size=25):
    img = cv2.imread(img)
    img = cv2.resize(img, (PADDING, PADDING), interpolation=cv2.INTER_LINEAR)
    imwidth, imheight = img.shape[:2]

    height = imheight // (imheight // block_size)
    width = imwidth // (imwidth // block_size)

    output_img = np.ones((PADDING, PADDING, 3), np.uint8)*255

    with ThreadPool(10) as pool:
        res = pool.starmap(
            makePixelate, [(img, output_img, imheight, imwidth, width, height, block_size)])
        pool.close()
        pool.join()
        return res[0]
