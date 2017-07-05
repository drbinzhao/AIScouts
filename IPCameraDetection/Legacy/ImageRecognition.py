
import numpy as np
import os, sys, getopt
import tflearn
import cv2
import matplotlib.pyplot as plt

from sklearn.cluster import MeanShift, estimate_bandwidth


from random import randint
from pyclustering.cluster.optics import optics
from pyclustering.cluster.kmeans import kmeans
from pyclustering.cluster import cluster_visualizer
from tflearn.layers.conv import conv_2d, max_pool_2d
from tflearn.layers.core import input_data,  dropout,  fully_connected
from tflearn.layers.estimator import regression

DATA_FOLDER = '/media/cf2017/levy/backup/tensorflow/images/'
crop_size_width = 128
crop_size_height = 128
image_width = 0
image_height = 0
image = None
move_ratio = 16
model_name = ''
model = None
count2 = 0
curr_position = [0, 0]
TF_Image_size = 128
layers = 0
LR = 0
visualize = False
POIX = []
POIY = []




def load_tfmodel(model_n):
    global model
    convnet = input_data(shape=[None, TF_Image_size, TF_Image_size, 1], name='input')

    for _ in range(layers):
        convnet = conv_2d(convnet, 32, 2, activation='relu')
        convnet = max_pool_2d(convnet, 2)

        convnet = conv_2d(convnet, 64, 2, activation='relu')
        convnet = max_pool_2d(convnet, 2)

    convnet = fully_connected(convnet, 1024, activation='relu')
    convnet = dropout(convnet, 0.8)

    convnet = fully_connected(convnet, 2, activation='softmax')
    convnet = regression(convnet, optimizer='adam', learning_rate=LR, loss='categorical_crossentropy', name='targets')

    model = tflearn.DNN(convnet, tensorboard_dir='log')

    if os.path.exists(DATA_FOLDER + model_n + '.meta'):
        model.load(DATA_FOLDER + model_n)
        print('model loaded!')
    else:
        print('model not found! ' + DATA_FOLDER + model_n)
        sys.exit(2)


def predict(crop):
    img = cv2.resize(crop, (TF_Image_size, TF_Image_size))
    data = img.reshape(TF_Image_size, TF_Image_size, 1)
    model_out = model.predict([data])[0]
    if np.argmax(model_out) == 0:
        return True
    return False


def validate_parking_place(curr_pos, orig_img, edit_image, move_visualize_image):
    found = 0
    curr_position2 = curr_pos.copy()
    not_found_y = 0
    edit_image2 = edit_image.copy()
    for y in range(int(crop_size_height / 3)):
        if curr_position2[1] + crop_size_height > image_height:
            break
        not_found_x = 0
        for x in range(int(crop_size_width / 3)):
            curr_position2[0] = int(curr_position2[0] + 2)
            if curr_position2[0] + crop_size_width > image_width:
                break
            crop = orig_img[curr_position2[1]:curr_position2[1] + crop_size_height,
                   curr_position2[0]:curr_position2[0] + crop_size_width]
            if predict(crop):
                found += 1
                cv2.circle(edit_image2, (
                    int(curr_position2[0] + crop_size_width / 2), int(curr_position2[1] + crop_size_height / 2)),
                           2,
                           (255, 0, 0), -1)
                not_found_x = 0
            else:
                not_found_x += 1
            if not_found_x > 10:
                break
            if visualize:
                cv2.rectangle(move_visualize_image,
                              (curr_position2[0], curr_position2[1]),
                              (curr_position2[0] + crop_size_width,
                               curr_position2[1] + crop_size_height),
                              (255, 0, 0),
                              2)
                cv2.imshow('main', move_visualize_image)
                cv2.waitKey(1)
                move_visualize_image = edit_image2.copy()
        if not_found_x > 10:
            not_found_y += 1
        else:
            not_found_y = 0
        if not_found_y > 5:
            break
        curr_position2[1] += 2
        curr_position2[0] = curr_pos[0]

    if found / ((crop_size_height / 2) * (crop_size_width / 2)) > 0.5:
        return True
    else:
        return False


def draw_heatmap2():
    global crop_size_width
    global crop_size_height
    global image
    global model_name
    global visualize
    visualize_img = None
    if visualize:
        visualize_img = image.copy()
    crop_size_height = crop_size_width
    curr_position = [0, 0]
    move_ratio_width = int(crop_size_width * 0.1)
    move_ratio_height = int(crop_size_height * 0.1)
    image2 = image.copy()
    if visualize:
        cv2.imshow('main', image)
        cv2.waitKey(1)
    while True:
        if curr_position[1] + crop_size_height >= image_height:
            break
        while True:
            crop = image2[curr_position[1]:curr_position[1] + crop_size_height, curr_position[0]:curr_position[0] + crop_size_width]
            if predict(crop):
                if validate_parking_place(curr_position, image2, image, visualize_img):
                    cv2.rectangle(image,
                                  (curr_position[0], curr_position[1]),
                                  (curr_position[0] + crop_size_width,
                                   curr_position[1] + crop_size_height),
                                  (255, 0, 0),
                                  2)
                    curr_position[0] = int(curr_position[0] + crop_size_width / 3)
                else:
                    curr_position[0] = int(curr_position[0] + move_ratio_width)

            else:
                curr_position[0] = int(curr_position[0] + move_ratio_width)
            if visualize:
                cv2.rectangle(visualize_img,
                              (curr_position[0], curr_position[1]),
                              (curr_position[0] + crop_size_width,
                               curr_position[1] + crop_size_height),
                              (255, 0, 0),
                              2)
                cv2.imshow('main', visualize_img)
                cv2.waitKey(1)
                visualize_img = image.copy()
            if curr_position[0] + crop_size_width >= image_width:
                break
        curr_position[1] = curr_position[1] + move_ratio_height
        curr_position[0] = 0

    if not os.path.exists('heatmaps'):
        os.makedirs('heatmaps')
    os.chdir('heatmaps')
    heatmap_img_file_name = (model_name + 'C' + str(crop_size_width) + '.jpg')
    cv2.imwrite(heatmap_img_file_name, image)

    os.chdir('..')



def draw_heatmap():
    global crop_size_width
    global crop_size_height
    global image
    global model_name
    global visualize
    global curr_position
    global POIX
    global POIY
    visualize_img = None
    if visualize:
        visualize_img = image.copy()
    crop_size_height = crop_size_width
    curr_position = [0, 0]
    move_ratio_width = int(crop_size_width * 0.1)
    move_ratio_height = int(crop_size_height * 0.1)

    image2 = image.copy()
    shift = [0, 0]
    if visualize:
        cv2.imshow('main', image)
        cv2.waitKey(1)
    for i in range(1):
        while True:
            if curr_position[1] + crop_size_height >= image_height:
                break
            else:
                curr_position[1] = curr_position[1] + move_ratio_height
                curr_position[0] = 0
            while True:
                crop = image2[curr_position[1]:curr_position[1] + crop_size_height, curr_position[0]:curr_position[0] + crop_size_width]
                if predict(crop):
                    cv2.circle(image, (int(curr_position[0] + crop_size_width / 2), int(curr_position[1] + crop_size_height / 2)),
                                  2,
                                  (255, 0, 0), -1)
                    POIX.append(curr_position[0] + crop_size_width / 2)
                    POIY.append(curr_position[1] + crop_size_height / 2)
                    curr_position[0] = int(curr_position[0] + move_ratio_width)
                else:
                    curr_position[0] = int(curr_position[0] + move_ratio_width)
                if visualize:
                    cv2.rectangle(visualize_img,
                                  (curr_position[0], curr_position[1]),
                                  (curr_position[0] + crop_size_width,
                                   curr_position[1] + crop_size_height),
                                  (255, 0, 0),
                                  2)
                    cv2.imshow('main', visualize_img)
                    cv2.waitKey(1)
                    visualize_img = image.copy()
                if curr_position[0] + crop_size_width >= image_width:
                    break
        shift[0] += 5
        shift[1] += 5
        crop_size_width += 10
        crop_size_height += 10
        curr_position = [shift[0], shift[1]]

    if not os.path.exists('heatmaps'):
        os.makedirs('heatmaps')
    os.chdir('heatmaps')
    heatmap_img_file_name = (model_name + 'C' + str(crop_size_width) + '.jpg')
    cv2.imwrite(heatmap_img_file_name, image)

    os.chdir('..')
    clusters = cluster_optics(POIX, POIY)
    park_mid_points = []
    #park_mid_points = cluster_meanshift(POIX, POIY)

    for i in range(len(clusters)):
        avg = 0
        count = 0
        for j in clusters[i]:
            count += 1
            avg += j
        park_mid_points.append([int(avg[0] / count), int(avg[1] / count)])

    image = image2.copy()
    for i in range(len(park_mid_points)):
         cv2.circle(image, (park_mid_points[i][0], park_mid_points[i][1]),
                      2,
                      (255, 0, 0), -1)
         #cv2.rectangle(image,
         #             (park_mid_points[i][0] - int(crop_size_width / 3),
         #              park_mid_points[i][1] - int(crop_size_height / 2)),
         #             (park_mid_points[i][0] + int(crop_size_width / 3),
         #              park_mid_points[i][1] + int(crop_size_height / 2)),
         #             (255, 0, 0),
         #             2)
    if visualize:
        cv2.imshow("main", image)
        cv2.waitKey()

    if not os.path.exists('results'):
        os.makedirs('results')
    os.chdir('results')
    cv2.imwrite(model_name + 'C' + str(crop_size_width) + 'CLOP' + '.jpg', image)
    os.chdir('..')

def cluster_meanshift(xs, ys):
    POI = []
    for i in range(len(xs)):
        POI.append([xs[i], ys[i]])
    POI = np.array(POI)

    bw = estimate_bandwidth(POI, quantile=0.085, n_samples=50)

    ms = MeanShift(bw, bin_seeding=True)
    ms.fit(POI)
    clusters = ms.cluster_centers_.astype(int)
    print(len(np.unique(ms.labels_)))

    ret = clusters

    return ret


def cluster_optics(xs, ys):
    POI = []
    for i in range(len(xs)):
        POI.append([xs[i], ys[i]])
    POI = np.array(POI)

    optics_instance = optics(POI, 27, 5)
    optics_instance.process()
    clusters = optics_instance.get_clusters()

    if visualize:
        vis = cluster_visualizer()
        vis.append_clusters(clusters, POI)
        vis.show()
    ret = []

    for i in range(len(clusters)):
        ret.append([])
        for j in range(len(clusters[i])):
            ret[i].append(POI[clusters[i][j]])

    return ret

def cluster_kmeans(xs, ys):
    POI = []
    for i in range(len(xs)):
        POI.append([xs[i], ys[i]])
    POI = np.array(POI)

    rand = []
    for i in range(14):
        r = randint(0, len(POI))
        rand.append(POI[r])


    kmeans_instance = kmeans(POI, rand, 4)
    kmeans_instance.process()
    clusters = kmeans_instance.get_clusters()

    if visualize:
        vis = cluster_visualizer()
        vis.append_clusters(clusters, POI)
        vis.show()
    ret = []

    for i in range(len(clusters)):
        ret.append([])
        for j in range(len(clusters[i])):
            ret[i].append(POI[clusters[i][j]])

    return ret


def init(argv):
    global image_width
    global image_height
    global crop_size_width
    global image
    global layers
    global LR
    global model_name
    global visualize
    try:
        opts, args = getopt.getopt(argv, "hi:c:m:r:l:v:", ["image", "crop", "model", "rate", "layers", "visualize"])
    except getopt.GetoptError:
        print('Usage: -i <image path> -c <crop width> -m <model path> -r <learning rate> -l <layers> -v <visualize(true/false)>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('Usage: -i <image path> -c <crop width> -m <model path>')
        elif opt in ('-i', '--image'):
            img_file = arg
        elif opt in ('-c', '--crop'):
            crop_size_width = int(arg)
        elif opt in ('-m', '--model'):
            model_path = 'models/' + arg
            model_name = arg
        elif opt in ('-r', '--rate'):
            LR = float(arg)
        elif opt in ('-l', '--layers'):
            layers = int(arg)
        elif opt in ('-v', '--visualize'):
            if arg.lower() == 'true':
                visualize = True
            else:
                visualize = False

    image = cv2.imread(img_file, cv2.IMREAD_GRAYSCALE)
    image_height, image_width = image.shape
    load_tfmodel(model_path)
    #for i in range(0, len(image)):
    #    for j in range(0, len(image[i])):
    #        if image[i][j] < 80:
    #            image[i][j] = 0
    #        else:
    #            image[i][j] = 100



def main(argv):
    cv2.namedWindow("main", cv2.WINDOW_AUTOSIZE)
    init(argv)
    draw_heatmap()


if __name__ == '__main__':
    main(sys.argv[1:])
