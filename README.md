python main_f2c.py --resume --resume_dir results/2018-04-23_03-38-31 

python main_f2c.py

# Feature trained on 10
python main_c2f.py --resume --resume_dir results/2018-04-23_03-38-31

# Feature trained on 2
python main_c2f.py --resume --resume_dir results/2018-04-23_16-45-22

# Test clustering
python test_clustering.py 2018-04-25_21-30-19

python main_c2f_resume.py --resume --resume_dir results/2018-04-24_21-12-54

CUDA_VISIBLE_DEVICES=0 nohup python main_f2c_cifar100.py &



# Feature trained on CIFAR-100 100
python main_c2f.py --resume --resume_dir results/2018-04-26_00-15-11

# Feature trained on CIFAR-100 20
python main_c2f.py --resume --resume_dir results/2018-04-25_19-48-32




# Train CIFAR10 with PyTorch

I'm playing with [PyTorch](http://pytorch.org/) on the CIFAR10 dataset.

## Pros & cons
Pros:
- Built-in data loading and augmentation, very nice!
- Training is fast, maybe even a little bit faster.
- Very memory efficient!

Cons:
- No progress bar, sad :(
- No built-in log.

## Accuracy
| Model             | Acc.        |
| ----------------- | ----------- |
| [VGG16](https://arxiv.org/abs/1409.1556)              | 92.64%      |
| [ResNet18](https://arxiv.org/abs/1512.03385)          | 93.02%      |
| [ResNet50](https://arxiv.org/abs/1512.03385)          | 93.62%      |
| [ResNet101](https://arxiv.org/abs/1512.03385)         | 93.75%      |
| [MobileNetV2](https://arxiv.org/abs/1801.04381)       | 94.43%      |
| [ResNeXt29(32x4d)](https://arxiv.org/abs/1611.05431)  | 94.73%      |
| [ResNeXt29(2x64d)](https://arxiv.org/abs/1611.05431)  | 94.82%      |
| [DenseNet121](https://arxiv.org/abs/1608.06993)       | 95.04%      |
| [PreActResNet18](https://arxiv.org/abs/1603.05027)    | 95.11%      |
| [DPN92](https://arxiv.org/abs/1707.01629)             | 95.16%      |

## Learning rate adjustment
I manually change the `lr` during training:
- `0.1` for epoch `[0,150)`
- `0.01` for epoch `[150,250)`
- `0.001` for epoch `[250,350)`

Resume the training with `python main.py --resume --lr=0.01`
