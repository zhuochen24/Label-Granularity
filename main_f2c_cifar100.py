# To run this, pay attention to this:
# define num_classes when initializing the model
# define f2c when calling train() and test()

'''Train CIFAR100 with PyTorch.'''
from __future__ import print_function

import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
import torch.backends.cudnn as cudnn

import torchvision
import torchvision.transforms as transforms

import os
import argparse

from models import *
from utils import progress_bar, adjust_optimizer, setup_logging
from torch.autograd import Variable
from datetime import datetime
import logging
import numpy as np
import pickle
import dataset


parser = argparse.ArgumentParser(description='PyTorch CIFAR100 Training')
parser.add_argument('--lr', default=0.1, type=float, help='learning rate')
parser.add_argument('--resume', '-r', action='store_true', help='resume from checkpoint')
parser.add_argument('--results_dir', metavar='RESULTS_DIR', default='./results',
                    help='results dir')
parser.add_argument('--resume_dir', default=None, help='resume dir')
parser.add_argument('--gpus', default='0', help='gpus used')
parser.add_argument('--f2c', type=int, default=None, help='whether use coarse label')
parser.add_argument('--categories', default=None, help='which classes to use')
parser.add_argument('--data_ratio', type=float, default=1., help='ratio of training data to use')
parser.add_argument('--add_layer', type=int, default=0, help='whether to add additional layer')
parser.add_argument('--dropout', type=float, default=.3, help='dropout rates, default 0.3')
parser.add_argument('--test_confmat', type=int, default=0, help='whether to test confmat')
parser.add_argument('--widen_factor', type=int, default=10, help='widen factor for net')
args = parser.parse_args()

if args.test_confmat == 1:
    from utils_confmat import *

args.save = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
if args.resume_dir is None:
    print('resume_dir is None')
    save_path = os.path.join(args.results_dir, args.save)
else:
    print('resume_dir is not None')
    save_path = args.resume_dir
if not os.path.exists(save_path):
    os.makedirs(save_path)
if args.resume_dir is None:
    setup_logging(os.path.join(save_path, 'log.txt'))
elif args.test_confmat == 1:
    setup_logging(os.path.join(save_path, 'log_confmat.txt'))
else:
    setup_logging(os.path.join(save_path, 'log1.txt'))
logging.info("saving to %s", save_path)
logging.info("run arguments: %s", args)

use_cuda = torch.cuda.is_available()
best_acc = 0  # best test accuracy
start_epoch = 0  # start from epoch 0 or last checkpoint epoch


coarse_classes = ('aquatic_mammals', 'fish', 'flowers', 'food_containers', 
                'fruit_and_vegetables', 'household_electrical_devices', 
                'household_furniture', 'insects', 'large_carnivores', 
                'large_man-made_outdoor_things', 'large_natural_outdoor_scenes', 
                'large_omnivores_and_herbivores', 'medium_mammals', 
                'non-insect_invertebrates', 'people', 'reptiles', 'small_mammals', 
                'trees', 'vehicles_1', 'vehicles_2')

fine_classes = ('apple', 'aquarium_fish', 'baby', 'bear', 'beaver', 'bed', 'bee', 
                'beetle', 'bicycle', 'bottle', 'bowl', 'boy', 'bridge', 'bus', 
                'butterfly', 'camel', 'can', 'castle', 'caterpillar', 'cattle', 
                'chair', 'chimpanzee', 'clock', 'cloud', 'cockroach', 'couch', 
                'crab', 'crocodile', 'cup', 'dinosaur', 'dolphin', 'elephant', 
                'flatfish', 'forest', 'fox', 'girl', 'hamster', 'house', 
                'kangaroo', 'keyboard', 'lamp', 'lawn_mower', 'leopard', 'lion', 
                'lizard', 'lobster', 'man', 'maple_tree', 'motorcycle', 
                'mountain', 'mouse', 'mushroom', 'oak_tree', 'orange', 'orchid', 
                'otter', 'palm_tree', 'pear', 'pickup_truck', 'pine_tree', 
                'plain', 'plate', 'poppy', 'porcupine', 'possum', 'rabbit', 
                'raccoon', 'ray', 'road', 'rocket', 'rose', 'sea', 'seal', 
                'shark', 'shrew', 'skunk', 'skyscraper', 'snail', 'snake', 
                'spider', 'squirrel', 'streetcar', 'sunflower', 'sweet_pepper', 
                'table', 'tank', 'telephone', 'television', 'tiger', 'tractor', 
                'train', 'trout', 'tulip', 'turtle', 'wardrobe', 'whale', 
                'willow_tree', 'wolf', 'woman', 'worm')

classes_c2f = {'aquatic_mammals': ['beaver','dolphin','otter','seal','whale'], 
                'fish': ['aquarium_fish','flatfish','ray','shark','trout'], 
                'flowers': ['orchid','poppy','rose','sunflower','tulip'], 
                'food_containers': ['bottle','bowl','can','cup','plate'], 
                'fruit_and_vegetables': ['apple','mushroom','orange','pear','sweet_pepper'], 
                'household_electrical_devices': ['clock','keyboard','lamp','telephone','television'], 
                'household_furniture': ['bed','chair','couch','table','wardrobe'], 
                'insects': ['bee','beetle','butterfly','caterpillar','cockroach'], 
                'large_carnivores': ['bear','leopard','lion','tiger','wolf'], 
                'large_man-made_outdoor_things': ['bridge','castle','house','road','skyscraper'], 
                'large_natural_outdoor_scenes': ['cloud','forest','mountain','plain','sea'], 
                'large_omnivores_and_herbivores': ['camel','cattle','chimpanzee','elephant','kangaroo'], 
                'medium_mammals': ['fox','porcupine','possum','raccoon','skunk'], 
                'non-insect_invertebrates': ['crab','lobster','snail','spider','worm'], 
                'people': ['baby','boy','girl','man','woman'], 
                'reptiles': ['crocodile','dinosaur','lizard','snake','turtle'], 
                'small_mammals': ['hamster','mouse','rabbit','shrew','squirrel'], 
                'trees': ['maple_tree','oak_tree','palm_tree','pine_tree','willow_tree'], 
                'vehicles_1': ['bicycle','bus','motorcycle','pickup_truck','train'], 
                'vehicles_2': ['lawn_mower','rocket','streetcar','tank','tractor']}

# classes_f2c = {}
# for idx,f_class in enumerate(fine_classes):
#     for jdx,c_class in enumerate(coarse_classes):
#         if f_class in classes_c2f[c_class]:
#             classes_f2c[idx] = jdx
#     if idx not in classes_f2c:
#         print(idx)
#         raise ValueError()

# # # Randomly re-define super classes
# # for i in range(50):
# #     idx = np.random.randint(0, 100)
# #     jdx = np.random.randint(0, 100)
# #     classes_f2c[idx], classes_f2c[jdx] = classes_f2c[jdx], classes_f2c[idx]
# # pickle.dump(classes_f2c, open(os.path.join(save_path, 'classes_f2c.pkl'), 'wb'))
# # logging.info('classes_f2c: {}'.format(classes_f2c))

# # load classes_f2c from pkl
# classes_f2c = pickle.load(open('results/2018-04-30_13-58-59/classes_f2c.pkl', 'rb'))
# logging.info('loading classes_f2c from: {}'.format('2018-04-30_13-58-59'))


if args.categories == 'animals':
    super_class_names = ['aquatic_mammals', 'fish', 'insects', 'large_carnivores', 'large_omnivores_and_herbivores', 'medium_mammals', 
                        'non-insect_invertebrates', 'people', 'reptiles', 'small_mammals']
    fine_class_names = []
    for super_class in super_class_names:
        fine_class_names += classes_c2f[super_class]
    class_idx = {name:idx for idx,name in enumerate(fine_classes)}
    class_list = [class_idx[name] for name in fine_class_names]
    classes_f2c = {}
    for idx,a_class in enumerate(class_list):
        for jdx,super_class in enumerate(super_class_names):
            if fine_classes[a_class] in classes_c2f[super_class]:
                classes_f2c[idx] = jdx
    print('classes_f2c: {}'.format(classes_f2c))
    if args.f2c == 1:
        NUM_CLASSES = 10
        if args.add_layer == 1:
            fine_cls = 50
        else:
            fine_cls = None
    else:
        NUM_CLASSES = 50
        fine_cls = None
elif args.categories == '5_classes':
    super_class_names = ['aquatic_mammals', 'large_carnivores', 'large_omnivores_and_herbivores', 'medium_mammals', 
                        'small_mammals']
    fine_class_names = []
    for super_class in super_class_names:
        fine_class_names += classes_c2f[super_class]
    class_idx = {name:idx for idx,name in enumerate(fine_classes)}
    class_list = [class_idx[name] for name in fine_class_names]
    classes_f2c = {}
    for idx,a_class in enumerate(class_list):
        for jdx,super_class in enumerate(super_class_names):
            if fine_classes[a_class] in classes_c2f[super_class]:
                classes_f2c[idx] = jdx
    print('classes_f2c: {}'.format(classes_f2c))
    if args.f2c == 1:
        NUM_CLASSES = 5
        if args.add_layer == 1:
            fine_cls = 25
        else:
            fine_cls = None
    else:
        NUM_CLASSES = 25
        fine_cls = None
elif args.categories == '15_classes':
    super_class_names = ['aquatic_mammals', 'fish', 'insects', 'large_carnivores', 'large_omnivores_and_herbivores', 'medium_mammals', 
                        'non-insect_invertebrates', 'people', 'reptiles', 'small_mammals', 'flowers', 'fruit_and_vegetables', 
                        'trees', 'vehicles_1', 'vehicles_2']
    fine_class_names = []
    for super_class in super_class_names:
        fine_class_names += classes_c2f[super_class]
    class_idx = {name:idx for idx,name in enumerate(fine_classes)}
    class_list = [class_idx[name] for name in fine_class_names]
    classes_f2c = {}
    for idx,a_class in enumerate(class_list):
        for jdx,super_class in enumerate(super_class_names):
            if fine_classes[a_class] in classes_c2f[super_class]:
                classes_f2c[idx] = jdx
    print('classes_f2c: {}'.format(classes_f2c))
    if args.f2c == 1:
        NUM_CLASSES = 15
        if args.add_layer == 1:
            fine_cls = 75
        else:
            fine_cls = None
    else:
        NUM_CLASSES = 75
        fine_cls = None
elif args.categories == None:
    classes_f2c = {}
    for idx,f_class in enumerate(fine_classes):
        for jdx,c_class in enumerate(coarse_classes):
            if f_class in classes_c2f[c_class]:
                classes_f2c[idx] = jdx
        if idx not in classes_f2c:
            print(idx)
            raise ValueError()
    class_list = [i for i in range(100)]
    if args.f2c == 1:
        NUM_CLASSES = 20
        if args.add_layer == 1:
            fine_cls = 100
        else:
            fine_cls = None
    else:
        NUM_CLASSES = 100
        fine_cls = None
else:
    raise ValueError

# Data
print('==> Preparing data..')
transform_train = transforms.Compose([
    transforms.RandomCrop(32, padding=4),
    transforms.RandomHorizontalFlip(),
    transforms.ToTensor(),
    transforms.Normalize((0.5071, 0.4867, 0.4408), (0.2675, 0.2565, 0.2761)),
])

transform_test = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize((0.5071, 0.4867, 0.4408), (0.2675, 0.2565, 0.2761)),
])

#trainset = torchvision.datasets.CIFAR100(root='/home/rzding/DATA', train=True, download=True, transform=transform_train)
trainset = dataset.data_cifar100.CIFAR100(root='/home/rzding/DATA', train=True, download=True, class_list=class_list, transform=transform_train, data_ratio=args.data_ratio)
trainloader = torch.utils.data.DataLoader(trainset, batch_size=128, shuffle=True, num_workers=2)

#testset = torchvision.datasets.CIFAR100(root='/home/rzding/DATA', train=False, download=True, transform=transform_test)
testset = dataset.data_cifar100.CIFAR100(root='/home/rzding/DATA', train=False, download=True, class_list=class_list, transform=transform_test, data_ratio=1.)
testloader = torch.utils.data.DataLoader(testset, batch_size=100, shuffle=False, num_workers=2)


# Model
if args.resume:
    # Load checkpoint.
    print('==> Resuming from checkpoint..')
    assert os.path.isdir(args.resume_dir)
    checkpoint = torch.load(os.path.join(args.resume_dir, 'ckpt.t7'))
    net = checkpoint['net']
    best_acc = checkpoint['acc']
    start_epoch = checkpoint['epoch']
else:
    print('==> Building model..')
    # net = VGG('VGG19')
    # net = ResNet18()
    #net = PreActResNet18(num_classes=100)
    net = wide_resnet(num_classes=NUM_CLASSES, fine_cls=fine_cls, dropout_rate=args.dropout, widen_factor=args.widen_factor)
    # net = GoogLeNet()
    # net = DenseNet121()
    # net = ResNeXt29_2x64d()
    # net = MobileNet()
    # net = MobileNetV2()
    # net = DPN92()
    # net = ShuffleNetG2()
    # net = SENet18()

logging.info("model structure: %s", net)
num_parameters = sum([l.nelement() for l in net.parameters()])
logging.info("number of parameters: %d", num_parameters)

if use_cuda:
    net.cuda()
    logging.info('gpus: {}'.format([int(ele) for ele in args.gpus]))
    net = torch.nn.DataParallel(net, device_ids=[int(ele) for ele in args.gpus])
    cudnn.benchmark = True

criterion = nn.CrossEntropyLoss()
optimizer = optim.SGD(net.parameters(), lr=args.lr, momentum=0.9, weight_decay=5e-4)
regime = {
    0: {'optimizer': 'SGD', 'lr': 1e-1,
        'weight_decay': 5e-4, 'momentum': 0.9, 'nesterov': False},
    int(60//args.data_ratio): {'lr': 2e-2},
    int(120//args.data_ratio): {'lr': 4e-3},
    int(160//args.data_ratio): {'lr': 8e-4},
}
logging.info('training regime: %s', regime)


# Training
def train(epoch, f2c=False):
    print('\nEpoch: %d' % epoch)
    net.train()
    train_loss = 0
    correct = 0
    correct_f2c = 0
    total = 0
    global optimizer
    optimizer = adjust_optimizer(optimizer, epoch, regime)
    for batch_idx, (inputs, targets) in enumerate(trainloader):
        if f2c:
            for idx,target in enumerate(targets):
                targets[idx] = classes_f2c[target]
        if use_cuda:
            inputs, targets = inputs.cuda(), targets.cuda()
        optimizer.zero_grad()
        inputs, targets = Variable(inputs), Variable(targets)
        outputs, _ = net(inputs)
        loss = criterion(outputs, targets)
        loss.backward()
        optimizer.step()

        train_loss += loss.data[0]
        _, predicted = torch.max(outputs.data, 1)
        total += targets.size(0)
        correct += predicted.eq(targets.data).cpu().sum()

        if f2c == False:
            predicted_np = predicted.cpu().numpy()
            for idx,a_predicted in enumerate(predicted_np):
                predicted_np[idx] = classes_f2c[a_predicted]
            targets_np = targets.data.cpu().numpy()
            for idx,a_target in enumerate(targets_np):
                targets_np[idx] = classes_f2c[a_target]
            correct_f2c += (predicted_np == targets_np).sum()

        #progress_bar(batch_idx, len(trainloader), 'Loss: %.3f | Acc: %.3f%% (%d/%d)'
        #    % (train_loss/(batch_idx+1), 100.*correct/total, correct, total))
        if batch_idx % 10 == 0:
            if f2c:
                logging.info('\n Epoch: [{0}][{1}/{2}]\t'
                            'Training Loss {train_loss:.3f} \t'
                            'Training Prec@1 {train_prec1:.3f} \t'
                            .format(epoch, batch_idx, len(trainloader),
                            train_loss=train_loss/(batch_idx+1), 
                            train_prec1=100.*correct/total))
            else:
                logging.info('\n Epoch: [{0}][{1}/{2}]\t'
                            'Training Loss {train_loss:.3f} \t'
                            'Training Prec@1 {train_prec1:.3f} \t'
                            'Training Prec@1 f2c {train_prec1_f2c:.3f} \t'
                            .format(epoch, batch_idx, len(trainloader),
                            train_loss=train_loss/(batch_idx+1), 
                            train_prec1=100.*correct/total,
                            train_prec1_f2c=100.*correct_f2c/total))


def test(epoch, f2c=False, train_f=True):
    global best_acc
    net.eval()
    test_loss = 0
    correct = 0
    total = 0
    for batch_idx, (inputs, targets) in enumerate(testloader):
        if f2c:
            for idx,target in enumerate(targets):
                targets[idx] = classes_f2c[target]
        if use_cuda:
            inputs, targets = inputs.cuda(), targets.cuda()
        inputs, targets = Variable(inputs, volatile=True), Variable(targets)
        outputs, _ = net(inputs)
        loss = criterion(outputs, targets)

        test_loss += loss.data[0]
        _, predicted = torch.max(outputs.data, 1)
        total += targets.size(0)
        if train_f and f2c:
            predicted_np = predicted.cpu().numpy()
            #print('predicted: {}'.format(predicted))
            #print('predicted_np: {}'.format(predicted_np))
            for idx,a_predicted in enumerate(predicted_np):
                predicted_np[idx] = classes_f2c[a_predicted]
            #correct += (predicted_np == targets.cpu().numpy()).sum()
            #print('targets: {}'.format(targets))
            correct += (predicted_np == targets.data.cpu().numpy()).sum()
        else:
            correct += predicted.eq(targets.data).cpu().sum()

        #progress_bar(batch_idx, len(testloader), 'Loss: %.3f | Acc: %.3f%% (%d/%d)'
        #    % (test_loss/(batch_idx+1), 100.*correct/total, correct, total))
    
    logging.info('\n Epoch: {0}\t'
                    'Testing Loss {test_loss:.3f} \t'
                    'Testing Prec@1 {test_prec1:.3f} \t\n'
                    .format(epoch, 
                    test_loss=test_loss/len(testloader), 
                    test_prec1=100.*correct/total))

    # Save checkpoint.
    acc = 100.*correct/total
    if acc > best_acc and args.resume_dir is None:
        print('Saving..')
        state = {
            'net': net.module if use_cuda else net,
            'acc': acc,
            'epoch': epoch,
        }
        torch.save(state, os.path.join(save_path, 'ckpt.t7'))
        best_acc = acc



if args.f2c == 1:
    for epoch in range(start_epoch, int(200//args.data_ratio)):
        train(epoch, f2c=True)
        #test(epoch, f2c=False)
        test(epoch, f2c=True, train_f=False)
elif args.f2c == 0:
    for epoch in range(start_epoch, int(200//args.data_ratio)):
        train(epoch, f2c=False)
        test(epoch, f2c=False)
        test(epoch, f2c=True, train_f=True)

# trainset = dataset.data_cifar100.CIFAR100(root='/home/rzding/DATA', train=True, download=True, class_list=class_list, transform=transform_train, data_ratio=args.data_ratio)
# trainloader = torch.utils.data.DataLoader(trainset, batch_size=100, shuffle=True, num_workers=2)

# testset = dataset.data_cifar100.CIFAR100(root='/home/rzding/DATA', train=False, download=True, class_list=class_list, transform=transform_test, data_ratio=1.)
# testloader = torch.utils.data.DataLoader(testset, batch_size=100, shuffle=False, num_workers=2)

# inter_confusion, intra_confusion = confusion(net, trainloader, classes_f2c)
# logging.info('Trainset inter_confusion: {}'.format(inter_confusion))
# logging.info('Trainset intra_confusion: {}'.format(intra_confusion))
# logging.info('Trainset ACR: {}'.format(inter_confusion/intra_confusion))
# inter_confusion, intra_confusion = confusion(net, testloader, classes_f2c)
# logging.info('Testset inter_confusion: {}'.format(inter_confusion))
# logging.info('Testset intra_confusion: {}'.format(intra_confusion))
# logging.info('Testset ACR: {}'.format(inter_confusion/intra_confusion))