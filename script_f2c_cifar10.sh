CUDA_VISIBLE_DEVICES=0 python main_f2c.py --f2c 0 --data_ratio 0.4 &&
CUDA_VISIBLE_DEVICES=0 python main_f2c.py --f2c 1 --data_ratio 0.4 &&
CUDA_VISIBLE_DEVICES=0 python main_f2c_cifar100.py --f2c 0 --data_ratio 0.4 --categories animals &&
CUDA_VISIBLE_DEVICES=0 python main_f2c_cifar100.py --f2c 1 --data_ratio 0.4 --categories animals &&
CUDA_VISIBLE_DEVICES=0 python main_f2c_cifar100.py --f2c 1 --data_ratio 0.2 &&
CUDA_VISIBLE_DEVICES=0 python main_f2c_cifar100.py --f2c 0 --data_ratio 0.4 &&
CUDA_VISIBLE_DEVICES=0 python main_f2c_cifar100.py --f2c 1 --data_ratio 0.4 