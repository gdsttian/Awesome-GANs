from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import tensorflow as tf
import numpy as np

import time
import dcgan
import image_utils as iu
from dataset import Dataset, DataIterator


dirs = {
    # 'cifar-10': 'D:\\ML\\cifar\\cifar-10-batches-py\\',
    # 'cifar-100': 'D:\\ML\\cifar\\cifar-100-python\\',
    # 'sample_output': 'D:\\ML\\cifar\\DCGAN\\',
    'cifar-10': '/home/zero/cifar/cifar-10-batches-py/',
    'cifar-100': '/home/zero/cifar/cifar-100-python/',
    'sample_output': '/home/zero/cifar/DCGAN/',
    'checkpoint': './model/checkpoint',
    'model': './model/LAPGAN-model.ckpt'
}
paras = {
    'epoch': 200,  # with GTX 1080 11gb, takes 4600s
    'batch_size': 64,
    'logging_interval': 750
}


def main():
    start_time = time.time()  # clocking start

    config = tf.ConfigProto()
    config.gpu_options.allow_growth = True
    with tf.Session(config=config) as s:
        # DCGAN model
        model = dcgan.DCGAN(s, batch_size=paras['batch_size'])

        # load model & graph & weight
        ckpt = tf.train.get_checkpoint_state('./model/')
        if ckpt and ckpt.model_checkpoint_path:
            # Restores from checkpoint
            model.saver.restore(s, ckpt.model_checkpoint_path)

            global_step = ckpt.model_checkpoint_path.split('/')[-1].split('-')[-1]
            print("[+] global step : %s" % global_step, " successfully loaded")
        else:
            global_step = 0
            print('[-] No checkpoint file found')
            # return

        # initializing variables
        tf.global_variables_initializer().run()

        # training, test data set
        dataset = Dataset(dirs['cifar-100'], name='cifar-100')  # Dataset(dirs['cifar-100'])
        dataset_iter = DataIterator(dataset.train_images, dataset.train_labels, paras['batch_size'])

        # import random
        # rnd = random.randint(0, dataset.valid_images.shape[0] / model.sample_size - 1)
        sample_images = dataset.valid_images[model.sample_size:model.sample_size].astype(np.float32) / 255.0
        sample_z = np.random.uniform(-1., 1., size=(model.sample_num, model.z_dim))  # noise

        d_overpowered = False  # G loss > D loss * 2

        step = int(global_step)
        cont = int(step / 750)
        for epoch in range(cont, cont + paras['epoch']):
            for batch_images, _ in dataset_iter.iterate():
                batch_images = batch_images.astype(np.float32) / 255.0
                batch_z = np.random.uniform(-1.0, 1.0, [paras['batch_size'], model.z_dim]).astype(np.float32)  # noise

                # update D network
                if not d_overpowered:
                    s.run(model.d_op, feed_dict={model.x: batch_images, model.z: batch_z})

                # update G network
                s.run(model.g_op, feed_dict={model.z: batch_z})

                if step % paras['logging_interval'] == 0:
                    batch_images = dataset.valid_images[:paras['batch_size']].astype(np.float32) / 255.0
                    batch_z = np.random.uniform(-1.0, 1.0, [paras['batch_size'], model.z_dim]).astype(np.float32)

                    d_loss, g_loss, summary = s.run([
                        model.d_loss,
                        model.g_loss,
                        model.merged
                    ], feed_dict={
                        model.x: batch_images,
                        model.z: batch_z
                    })

                    # print loss
                    print("[+] Epoch %03d Step %05d => " % (epoch, step),
                          "D loss : {:.8f}".format(d_loss), " G loss : {:.8f}".format(g_loss))

                    # update overpowered
                    d_overpowered = d_loss < g_loss / 2

                    # training G model with sample image and noise
                    samples = s.run(model.G, feed_dict={
                        model.x: sample_images,
                        model.z: sample_z
                    })

                    # summary saver
                    model.writer.add_summary(summary, step)

                    # export image generated by model G
                    sample_image_height = 8
                    sample_image_width = 8
                    sample_dir = dirs['sample_output'] + 'train_{0}_{1}.png'.format(epoch, step)

                    # Generated image save
                    iu.save_images(samples, size=[sample_image_height, sample_image_width], image_path=sample_dir)

                    # model save
                    model.saver.save(s, dirs['model'], global_step=step)

                step += 1

        end_time = time.time() - start_time

        # elapsed time
        print("[+] Elapsed time {:.8f}s".format(end_time))

        # close tf.Session
        s.close()

if __name__ == '__main__':
    main()
