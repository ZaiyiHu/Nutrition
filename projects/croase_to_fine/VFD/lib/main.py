import os

import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import models
from collections import namedtuple
import numpy as np
import json
import random
from torch.backends import cudnn
import shutil
import time
import pandas as pd

from models.Network_ViT import base_patch16_384_gap
from config.args_parse import args_parser
from core.function import train,read_ann_json,evaluate,MylossFunc
from models.network import ResNet, Bottleneck
from dataset.dataset import VFD
from evaluation.compute_eval_statistics import calMAE
from utils.util import get_anchor

CATEGORY = ["volume"]

### set certain seed ###
def fix_randomness(seed):
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    np.random.seed(seed)
    random.seed(seed)
    # cudnn related setting
    cudnn.benchmark = False
    cudnn.deterministic = True
    cudnn.enabled = True

def main(args,i,ticks):
    fix_randomness(args.seed)
    torch.cuda.empty_cache()
    batch_size = args.batch_size
    output_dim = args.output_dim
    found_lr = args.found_lr
    segment = args.segment
    epoch = args.epoch
    seed = args.seed

    train_img_dir = '/data1/zaiyihu/Datasets/Nutrition_data/VFD/data/vfdl/train_resize'
    test_img_dir = '/data1/zaiyihu/Datasets/Nutrition_data/VFD/data/vfdl/test_resize'

    train_json_file = './dataset/vfdl_Bin_number10/VFD_volume_train_seg'+str(segment)+'.json'
    test_json_file = './dataset/vfdl_Bin_number10/VFD_volume_test_seg'+str(segment)+'.json'

    train_anchor = get_anchor(segment,i,'train')
    test_anchor = get_anchor(segment,i,'test')
    # print(train_anchor)
    # print(test_anchor)


    #### dataset #####
    train_anns = read_ann_json(train_json_file)
    train_fun = VFD(train_img_dir, train_anns, phase='train',category=i)
    train_loader = torch.utils.data.DataLoader(train_fun, batch_size=batch_size, shuffle=True,num_workers = 8,pin_memory = True)

    test_anns = read_ann_json(test_json_file)
    test_fun = VFD(test_img_dir, test_anns, phase='test',category=i)
    test_loader = torch.utils.data.DataLoader(test_fun, batch_size=batch_size, shuffle=False,num_workers = 8,pin_memory = True)
    #### dataset #####

    ##### network #####
    if args.model == 'ResNet':
        ResNetConfig = namedtuple('ResNetConfig', ['block', 'n_blocks', 'channels'])
        resnet50_config = ResNetConfig(block=Bottleneck,
                                       n_blocks=[3, 4, 6, 3],
                                       channels=[64, 128, 256, 512])

        resnet50 = models.resnet50(pretrained=True)
        model = ResNet(resnet50_config, segment)
        pretrained_dict = resnet50.state_dict()
        model_dict = model.state_dict()
        pretrained_dict = {k: v for k, v in pretrained_dict.items() if k in model_dict}

        model_dict.update(pretrained_dict)

        #Load the state dict we really need
        model.load_state_dict(model_dict,True)
    elif args.model == 'ViT':
        model = base_patch16_384_gap()

    model = model.cuda()
    learnable_pam = MylossFunc()
    #### network #####

    #### optimizer #####
    if args.model == 'ResNet':

        params = [
            {'params': model.conv1.parameters(), 'lr': found_lr / 10},
            {'params': model.bn1.parameters(), 'lr': found_lr / 10},
            {'params': model.layer1.parameters(), 'lr': found_lr / 8},
            {'params': model.layer2.parameters(), 'lr': found_lr / 6},
            {'params': model.layer3.parameters(), 'lr': found_lr / 4},
            {'params': model.layer4.parameters(), 'lr': found_lr / 2},
            {'params': model.fc_self.parameters(), 'lr': found_lr / 2},
            {'params': model.fc1.parameters(), 'lr': found_lr / 2},
            {'params': model.fc2.parameters(), 'lr': found_lr / 2},
            {'params': model.lastlayer.parameters()},
            {'params': learnable_pam.parameters()}
        ]

        #optimizer = optim.RMSprop(params, lr=found_lr,momentum= 0.9,weight_decay= 0.9,eps=1.0)
        #optimizer = optim.Adam(params, lr=found_lr,weight_decay=0.9,eps=1.0)
        optimizer = optim.Adam(params, lr=found_lr)
    else:
        optimizer = torch.optim.Adam(
            [  #
                {'params': model.parameters(), 'lr': args.found_lr},
            ], lr=args.found_lr)
    #### optimizer #####

    food_MAE_pre = 100
    for iepoch in range(epoch):
        loss_sec,loss_off = train(args,train_loader, model,learnable_pam, optimizer,batch_size,segment,train_anchor)
        print('epoch ' + str(iepoch) + '\n'+ f'\tTrain Section_Loss: {loss_sec:.3f}'+'\n'+f'\tTrain Offset_Loss: {loss_off:.3f}\n')
        pre_res = evaluate(test_loader,model,learnable_pam,batch_size,segment,test_anchor,i)
        #predcts_test = evaluate(model,test_loader,batch_size)

        tmp_MAE, tmp_MAE_pre,each_prediction = calMAE(pre_res, i)
        with open("result/" + ticks +'lr'+str(found_lr)+'td'+str(threshold) + 'epoch'+str(epoch) + "VFD_prediction.txt", "a") as f:
            f.write(f'{tmp_MAE:.3f}   {tmp_MAE_pre:.3f}%\n')
        if (food_MAE_pre > tmp_MAE_pre):
            food_MAE = tmp_MAE
            food_MAE_pre = tmp_MAE_pre
            print(f'\t ' + i + f'_MAE:{food_MAE:.3f}\n' + f'\t ' + i + f'_MAE:{food_MAE_pre:.3f}')
            print(each_prediction)
            torch.save(model, i + ticks + args.model + ' ViT+LLS_' + 'model.pth')
    print(f'\t ' + i + f'_MAE:{food_MAE:.3f}\n' + f'\t ' + i + f'_MAE:{food_MAE_pre:.3f}')
    print(each_prediction)

if __name__ == '__main__':
    args= args_parser()
    batch_size = args.batch_size
    output_dim = args.output_dim
    found_lr = args.found_lr
    segment = args.segment
    epoch = args.epoch
    seed = args.seed
    threshold = args.threshold
    os.environ["CUDA_VISIBLE_DEVICES"] = args.CUDA_DEVICE

    ticks = time.strftime("%Y-%m-%d %H:%M", time.localtime())
    print(ticks)

    with open("result/" + ticks +'lr'+str(found_lr)+'td'+str(threshold) + 'epoch'+str(epoch) + "VFD_prediction.txt","a") as f:
        f.write("data   percent\n")

    for i in CATEGORY:
        main(args,i,ticks)

    tick2 = time.strftime("%Y-%m-%d %H:%M", time.localtime())
    print(tick2)
