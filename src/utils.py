# MIT License
#
# Copyright (c) 2018 Haoxintong
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
"""utils of this project"""

import numpy as np
import matplotlib

matplotlib.use('Agg')
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.patheffects as PathEffects

import sklearn
from mxnet import gluon
from mxnet.gluon.data.vision import transforms
from src.data.verification import FaceVerification


def plot_result(embeds, labels, output_path):
    # vis, plot code from https://github.com/pangyupo/mxnet_center_loss
    num = len(labels)
    names = dict()
    for i in range(10):
        names[i] = str(i)
    palette = np.array(sns.color_palette("hls", 10))
    f = plt.figure(figsize=(8, 8))
    ax = plt.subplot(aspect='equal')
    sc = ax.scatter(embeds[:, 0], embeds[:, 1], lw=0, s=40,
                    c=palette[labels.astype(np.int)])
    ax.axis('off')
    ax.axis('tight')

    # We add the labels for each digit.
    txts = []
    for i in range(10):
        # Position of each label.
        xtext, ytext = np.median(embeds[labels == i, :], axis=0)
        txt = ax.text(xtext, ytext, names[i])
        txt.set_path_effects([
            PathEffects.Stroke(linewidth=5, foreground="w"),
            PathEffects.Normal()])
        txts.append(txt)
    plt.savefig(output_path)


def inf_train_gen(loader):
    """
    Using iterations train network.
    :param loader: Dataloader
    :return: batch of data
    """
    while True:
        for batch in loader:
            yield batch


transform_test = transforms.Compose([
    transforms.ToTensor()
])

_transform_train = transforms.Compose([
    transforms.RandomBrightness(0.3),
    transforms.RandomContrast(0.3),
    transforms.RandomSaturation(0.3),
    transforms.RandomFlipLeftRight(),
    transforms.ToTensor()
])


def transform_train(data, label):
    im = _transform_train(data)
    return im, label


def validate(net, ctx, val_datas, targets, nfolds=10, norm=True):
    metric = FaceVerification(nfolds)
    results = []
    for loader, name in zip(val_datas, targets):
        metric.reset()
        for i, batch in enumerate(loader):
            data0s = gluon.utils.split_and_load(batch[0][0], ctx, even_split=False)
            data1s = gluon.utils.split_and_load(batch[0][1], ctx, even_split=False)
            issame_list = gluon.utils.split_and_load(batch[1], ctx, even_split=False)

            embedding0s = [net(X)[0] for X in data0s]
            embedding1s = [net(X)[0] for X in data1s]
            if norm:
                embedding0s = [sklearn.preprocessing.normalize(e.asnumpy()) for e in embedding0s]
                embedding1s = [sklearn.preprocessing.normalize(e.asnumpy()) for e in embedding1s]

            for embedding0, embedding1, issame in zip(embedding0s, embedding1s, issame_list):
                metric.update(issame, embedding0, embedding1)

        tpr, fpr, accuracy, val, val_std, far, accuracy_std = metric.get()
        results.append("{}: {:.6f}+-{:.6f}".format(name, accuracy, accuracy_std))
    return results
