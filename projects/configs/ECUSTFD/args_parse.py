import argparse


r""""
About setting some hyperparameters
"""
def args_parser():
    parser = argparse.ArgumentParser(description='ECUSTFD set')
    parser.add_argument('--CUDA_DEVICE',type = str,default='1')
    parser.add_argument('--model', type=str, default='ResNet')
    parser.add_argument('--batch_size',type = int, default=16)
    parser.add_argument('--output_dim',type = int,default=4096)
    parser.add_argument('--found_lr',type = float,default=5e-4)
    parser.add_argument('--weight_decay', type=float, default=5 * 1e-4,
                        help='weight decay')
    parser.add_argument('--segment',type = int,default=10)
    parser.add_argument('--epoch', type = int,default=30)
    parser.add_argument('--alpha', type = float,default=1)
    parser.add_argument('--beta', type = float,default=1)
    parser.add_argument('--threshold',type = float,default=0.1)
    parser.add_argument('--seed', type = int,default=1)
    parser.add_argument('--pre', type=str, default=None,
                        help='pre-trained model directory')
    args = parser.parse_args()
    return args

if __name__ == '__main__':
    arg = args_parser()