import numpy as np
import matplotlib.pyplot as plt
from scipy.misc import imread
from scipy.signal import convolve2d as c2d
from scipy.ndimage.filters import convolve
import skimage.color as sk
import os

# ---- constants ---- #
LOWEST_RES = 16
# ------------------- #


def build_gaussian_pyramid(im, max_levels, filter_size):
    """
    :param im: a grayscale image with double values in [0, 1]
    :param max_levels:  the maximal number of levels in the resulting pyramid
    :param filter_size:  the size of the Gaussian filter to be used
    in constructing the pyramid filter .
    :return: pyr: a standard python array with maximum length of max_levels, where each element of the
    array is a grayscale.
    :return: filter_vec: 1D-row of size filter_size used for the pyramid construction.
    """
    pyr = [im]  # to hold re-sized images
    rows, cols = im.shape[0], im.shape[1]
    filter_vec = make_filter_to_size(filter_size)  # make filter in size
    for i in range(1, max_levels):
        resize_factor = 2 ** i
        if rows / resize_factor > LOWEST_RES or cols / resize_factor > LOWEST_RES:
            # blurs and reduce image to half in each dim.
            pyr.append(reduce_image(im, filter_vec, i))
        else:  # got to lowest resolution allowed
            return pyr, filter_vec
    return pyr, filter_vec


def build_laplacian_pyramid(im, max_levels, filter_size):
    """
    :param im: a grayscale image with double values in [0, 1]
    :param max_levels:  the maximal number of levels in the resulting pyramid
    :param filter_size:  the size of the Gaussian filter to be used
    in constructing the pyramid filter .
    :return: pyr: a standard python array with maximum length of max_levels, where each element of the
    array is a grayscale.
    :return: filter_vec: 1D-row of size filter_size used for the pyramid construction.
    """
    # make gaussian pyramid
    g_pyr, filter_vec = build_gaussian_pyramid(im, max_levels, filter_size)
    # initial laplacian pyramid
    l_pyr = []

    # calculate the laplacian level
    for i in range(max_levels - 1):
        expanded = expand_image(g_pyr[i + 1], filter_vec)
        l_im = g_pyr[i] - expanded
        l_pyr.append(l_im)

    # add last level image
    l_pyr.append(g_pyr[-1])

    return l_pyr, filter_vec


def laplacian_to_image(lpyr, filter_vec, coeff):
    """

    :param lpyr: Laplacian pyramid
    :param filter_vec: filter that are generated by the second function
    :param coeff: is a vector
    :return: image: reconstruction of an image
    """

    # extract original image
    r_img = lpyr[-1] * coeff[-1]

    # do opposite process of make laplacian pyr, meaning expand image and add to previous level
    levels = len(lpyr) - 2  # start iterate from second level from the end
    for i in range(levels + 1):
        r_img = (lpyr[levels - i] * coeff[levels - i]) + expand_image(r_img, filter_vec)
    return r_img


def render_pyramid(pyr, levels):
    """

    :param pyr: is either a Gaussian or Laplacian pyramid
    :param levels: is the number of levels to present in the result
    :return: res: is a single black image in which the pyramid levels of the given pyramid pyr are stacked
    horizontally (after stretching the values to [0, 1])
    """
    # set pyr properties
    levels = min(levels, len(pyr))
    pyr_h = pyr[0].shape[0]
    pyr_w = sum(pyr[i].shape[1] for i in range(levels))
    res = np.zeros([pyr_h, pyr_w]).astype(np.float64)

    # stack images
    marker = 0
    for i in range(levels):
        v_max, h_max = pyr[i].shape[0], pyr[i].shape[1]
        # input image and normalize

        res[0:v_max, marker:(marker + h_max)] = norm_pyramid(pyr[i])
        marker = marker + h_max

    return res


def display_pyramid(pyr, levels):
    """
    :param pyr: is either a Gaussian or Laplacian pyramid
    :param levels: s is the number of levels to present in the result ? max_levels
    """
    #   render pyramid
    pyr_disp = render_pyramid(pyr, levels)

    # display pyramid
    plt.figure()
    plt.imshow(pyr_disp, cmap=plt.cm.gray)
    plt.show()


def pyramid_blending(im1, im2, mask, max_levels, filter_size_im, filter_size_mask):
    """
    :param im1:  input grayscale image to be blended.
    :param im2:  input grayscale image to be blended.
    :param mask: is a boolean mask containing True and False representing which parts of im1 and im2
    should appear in the blended image
    :param max_levels: is the max_levels parameter to use when generating the Gaussian and Laplacian
    pyramids.
    :param filter_size_im: is the size of the Gaussian filter which defining the filter used in the
    construction of the Laplacian pyramids of im1 and im2.
    :param filter_size_mask:is the size of the Gaussian filter which defining the filter used in the
    construction of the Gaussian pyramid of mask.
    :return: im_blend: Implemented pyramid blending as described in the lecture
    """

    # initialize pyramids
    lpyr_1, filter_vec_1 = build_laplacian_pyramid(im1, max_levels, filter_size_im)
    lpyr_2, filter_vec_2 = build_laplacian_pyramid(im2, max_levels, filter_size_im)
    g_m, garbage_vec = build_gaussian_pyramid(mask.astype(np.float64), max_levels, filter_size_mask)
    # blend as shown on ex.
    L_out = [0] * len(lpyr_1)
    for k in range(len(lpyr_1)):
        L_out[k] = (g_m[k] * lpyr_1[k])  + ((1 - g_m[k]) * lpyr_2[k])

    # transform to image and clip
    im_blend = laplacian_to_image(L_out, filter_vec_1, np.ones(len(lpyr_1)))
    return np.clip(im_blend, 0, 1)


def blending_example1():
    """
    blend two images and a mask
    """
    # read images
    im1 = read_image(relpath('externals/im4.jpg'), 2)
    im2 = read_image(relpath('externals/im5.jpg'), 2)
    mask = read_image(relpath('externals/im6.PNG'), 1) > 127/255

    # define attributes
    max_levels, filter_size_im, filter_size_mask = 5, 5, 3

    # blend with 3 channels
    im_blend = blend_RGB(im1, im2, mask, max_levels, filter_size_im, filter_size_mask)
    return im1, im2, mask, im_blend


def blending_example2():
    """
    blend two images and a mask
    """
    # read images
    im1 = read_image(relpath('externals/im1.jpg'), 2)
    im2 = read_image(relpath('externals/im2.jpg'), 2)
    mask = read_image(relpath('externals/im3.PNG'), 1) > 127/255

    # define attributes
    max_levels, filter_size_im, filter_size_mask = 5, 5, 3

    # blend with 3 channels
    im_blend = blend_RGB(im1, im2, mask, max_levels, filter_size_im, filter_size_mask)
    return im1, im2, mask, im_blend


# ////\\\\////\\\\////\\\\////\\\\////\\\\#
#             helper functions              #
# \\\\////\\\\////\\\\////\\\\////\\\\////#


def expand_image(im, filter_vec):
    """
    the function expend reduced image by padding and blur
    :param im: the image to expend
    :param filter_vec: the vector to blur by it
    :return: the image twice its size
    """
    # pad image with zeros to twice the size
    rows, cols = im.shape[0], im.shape[1]
    expand_im = np.zeros([rows * 2, cols * 2])
    expand_im[::2, ::2] = im

    # blur image each polarization
    expand_im = convolve(expand_im, filter_vec * 2)
    expand_im = convolve(expand_im, filter_vec.transpose() * 2)
    return expand_im


def reduce_image(im, filter_vec, i):
    """
    the function reduces the image size by two. blur before resizing.
    :param im: original image
    :param filter_vec: vector to filter by
    :return: image size down by half
    """
    #   blur
    reduced_im = convolve(im, filter_vec)
    reduced_im = convolve(reduced_im, filter_vec.transpose())

    #   re-size
    reduced_im = reduced_im[::2 ** i, ::2 ** i]

    return reduced_im


def read_image(filename, representation):
    """
    :param filename: the file name of the image to open
    :param representation: 1 for grayscale format, 2 for RGB format
    :return: image as float 64 in the selected format
    """
    im = imread(filename).astype(np.float64)
    im = sk.rgb2gray(im)/255 if representation == 1 else im / 255
    return im


def make_filter_to_size(size):
    """
    make a filter mask to size as an image
    :param size: the size of desired mask
    :return: the filter in the stated size, normalized
    """
    # make blur mask filter based on the vector and kernel size
    blur_vector = np.matrix(np.array([1, 1]))
    blur_mask = c2d(blur_vector, blur_vector)  # initial mask

    for i in range(size - 3):  # up-size mask to kernel size
        blur_mask = c2d(blur_mask, blur_vector)

    # normalize filter
    blur_mask = blur_mask / np.sum(blur_mask)
    return blur_mask


def norm_pyramid(pyr):
    """
    normalize pyramid values
    :param pyr: pyramid
    :return: normalized pyramid
    """
    max_pixel, min_pixel = np.nanmax(pyr), np.nanmin(pyr)
    return (pyr - min_pixel) / (max_pixel - min_pixel)


def relpath(filename):
    """
    function from ex to upload images
    """
    return os.path.join(os.path.dirname(__file__), filename)


def blend_RGB(im1, im2, mask, max_levels, filter_size_im, filter_size_mask):
    im_blend = np.zeros((im1.shape[0], im1.shape[1], 3)).astype(np.float64)
    for i in range(3):
        im_blend[:, :, i] = pyramid_blending(im1[:, :, i], im2[:, :, i], mask, max_levels, filter_size_im,
                                             filter_size_mask)

    display_blend(im1, im2, mask, im_blend)
    return im_blend


def display_blend(im1, im2, mask, im_blend):
    """
    display all the involved images
    """
    plt.figure()  # open figure to plot on

    # set image to plot number
    plt.subplot(2, 2, 1)
    plt.imshow(im1)
    plt.subplot(2, 2, 2)
    plt.imshow(im2)
    plt.subplot(2, 2, 3)
    plt.imshow(mask, cmap=plt.cm.gray)
    plt.subplot(2, 2, 4)
    plt.imshow(im_blend)

    # show must go on
    plt.show()


#blending_example1()

blending_example2()