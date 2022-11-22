import os
import shutil


def clean():
    shutil.rmtree('blocks')
    os.mkdir('blocks')


if __name__ == '__main__':
    clean()
