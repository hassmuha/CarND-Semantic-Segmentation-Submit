import os.path
import tensorflow as tf
import helper
import warnings
from distutils.version import LooseVersion
import project_tests as tests


# Check TensorFlow Version
assert LooseVersion(tf.__version__) >= LooseVersion('1.0'), 'Please use TensorFlow version 1.0 or newer.  You are using {}'.format(tf.__version__)
print('TensorFlow Version: {}'.format(tf.__version__))

# Check for a GPU
if not tf.test.gpu_device_name():
    warnings.warn('No GPU found. Please use a GPU to train your neural network.')
else:
    print('Default GPU Device: {}'.format(tf.test.gpu_device_name()))


def load_vgg(sess, vgg_path):
    """
    Load Pretrained VGG Model into TensorFlow.
    :param sess: TensorFlow Session
    :param vgg_path: Path to vgg folder, containing "variables/" and "saved_model.pb"
    :return: Tuple of Tensors from VGG model (image_input, keep_prob, layer3_out, layer4_out, layer7_out)
    """
    # TODO: Implement function
    #   Use tf.saved_model.loader.load to load the model and weights

    vgg_tag = 'vgg16'
    vgg_input_tensor_name = 'image_input:0' # For Feeding image
    vgg_keep_prob_tensor_name = 'keep_prob:0' # Because it can be o.5 during learning and 1.0 during testing
    vgg_layer3_out_tensor_name = 'layer3_out:0' # For FCN-8s
    vgg_layer4_out_tensor_name = 'layer4_out:0' # For FCN-8s
    vgg_layer7_out_tensor_name = 'layer7_out:0' # For FCN-8s

    tf.saved_model.loader.load(sess,[vgg_tag],vgg_path)
    graph = tf.get_default_graph()
    vgg_input = graph.get_tensor_by_name(vgg_input_tensor_name)
    vgg_keep_prob = graph.get_tensor_by_name(vgg_keep_prob_tensor_name)
    vgg_layer3 = graph.get_tensor_by_name(vgg_layer3_out_tensor_name)
    vgg_layer4 = graph.get_tensor_by_name(vgg_layer4_out_tensor_name)
    vgg_layer7 = graph.get_tensor_by_name(vgg_layer7_out_tensor_name)

    return vgg_input, vgg_keep_prob, vgg_layer3, vgg_layer4, vgg_layer7
tests.test_load_vgg(load_vgg, tf)


def layers(vgg_layer3_out, vgg_layer4_out, vgg_layer7_out, num_classes):
    """
    Create the layers for a fully convolutional network.  Build skip-layers using the vgg layers.
    :param vgg_layer3_out: TF Tensor for VGG Layer 3 output
    :param vgg_layer4_out: TF Tensor for VGG Layer 4 output
    :param vgg_layer7_out: TF Tensor for VGG Layer 7 output
    :param num_classes: Number of classes to classify
    :return: The Tensor for the last layer of output
    """
    # TODO: Implement function
    # First used the approach as described in project walkthrough video but later
    # changed to scale the layer 7 and 4 first before applying 1x1 convolution

    #Upsampling : x4 to make the size equal to scaled layer 4 and layer 3
    layer7_4x = tf.layers.conv2d_transpose(vgg_layer7_out, num_classes, 8, 4,padding='same',
                kernel_initializer= tf.random_normal_initializer(stddev=0.01),
                kernel_regularizer=tf.contrib.layers.l2_regularizer(1e-3))
    #1x1 convolution to make the output layers equal to num_classes
    layer7_conv1x1 = tf.layers.conv2d(layer7_4x, num_classes, 1, padding='same',
                    kernel_initializer= tf.random_normal_initializer(stddev=0.01),
                    kernel_regularizer=tf.contrib.layers.l2_regularizer(1e-3))
    # Upsampling : x2 to make the size equal to layer3
    layer4_2x = tf.layers.conv2d_transpose(vgg_layer4_out, num_classes, 4, 2,padding='same',
                    kernel_initializer= tf.random_normal_initializer(stddev=0.01),
                    kernel_regularizer=tf.contrib.layers.l2_regularizer(1e-3))
    #1x1 convolution to make the output layers equal to num_classes
    layer4_conv1x1 = tf.layers.conv2d(layer4_2x, num_classes, 1, padding='same',
                    kernel_initializer= tf.random_normal_initializer(stddev=0.01),
                    kernel_regularizer=tf.contrib.layers.l2_regularizer(1e-3))
    #Add the upsampled 7th layer with 4th layer
    layer74 = tf.add(layer7_conv1x1, layer4_conv1x1)

    #1x1 convolution to make the output layers equal to num_classes
    layer3_conv1x1 = tf.layers.conv2d(vgg_layer3_out, num_classes, 1, padding='same',
                    kernel_initializer= tf.random_normal_initializer(stddev=0.01),
                    kernel_regularizer=tf.contrib.layers.l2_regularizer(1e-3))
    #Add the upsampled 7th layer with 3th layer
    layer743 = tf.add(layer74, layer3_conv1x1)
    # Upsampling : x8 to make the size equal to original image size
    Output = tf.layers.conv2d_transpose(layer743, num_classes, 16, 8,padding='same',
                    kernel_initializer= tf.random_normal_initializer(stddev=0.01),
                    kernel_regularizer=tf.contrib.layers.l2_regularizer(1e-3))
    return Output

tests.test_layers(layers)


def optimize(nn_last_layer, correct_label, learning_rate, num_classes):
    """
    Build the TensorFLow loss and optimizer operations.
    :param nn_last_layer: TF Tensor of the last layer in the neural network
    :param correct_label: TF Placeholder for the correct label image
    :param learning_rate: TF Placeholder for the learning rate
    :param num_classes: Number of classes to classify
    :return: Tuple of (logits, train_op, cross_entropy_loss)
    """
    # TODO: Implement function
    logits = tf.reshape(nn_last_layer, (-1, num_classes))
    # calculate the cross entropy loss
    cross_entropy_loss = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits(logits=logits, labels=correct_label))
    # for adding regularization loss terms
    reg_losses = tf.get_collection(tf.GraphKeys.REGULARIZATION_LOSSES)
    reg_constant = 0.01
    cross_entropy_loss_with_l2 = cross_entropy_loss + reg_constant * sum(reg_losses)

    optimizer = tf.train.AdamOptimizer(learning_rate = learning_rate)
    training_operation = optimizer.minimize(cross_entropy_loss_with_l2)

    return logits, training_operation, cross_entropy_loss_with_l2
tests.test_optimize(optimize)


def train_nn(sess, epochs, batch_size, get_batches_fn, train_op, cross_entropy_loss, input_image,
             correct_label, keep_prob, learning_rate):
    """
    Train neural network and print out the loss during training.
    :param sess: TF Session
    :param epochs: Number of epochs
    :param batch_size: Batch size
    :param get_batches_fn: Function to get batches of training data.  Call using get_batches_fn(batch_size)
    :param train_op: TF Operation to train the neural network
    :param cross_entropy_loss: TF Tensor for the amount of loss
    :param input_image: TF Placeholder for input images
    :param correct_label: TF Placeholder for label images
    :param keep_prob: TF Placeholder for dropout keep probability
    :param learning_rate: TF Placeholder for learning rate
    """
    # TODO: Implement function
    sess.run(tf.global_variables_initializer())
    print("Training...")
    print()
    for epoch in range(epochs):
        print("EPOCH {} ...".format(epoch+1))
        total_loss = 0
        total_train_size = 0
        for image, label in get_batches_fn(batch_size):
             _ , loss = sess.run([train_op, cross_entropy_loss],feed_dict={input_image: image, correct_label: label, keep_prob: 0.5})
             actual_batch_size = image.shape[0]
             total_loss = total_loss + (loss * actual_batch_size)
             total_train_size = total_train_size + actual_batch_size
        # print average loss calculated over all training set
        print(total_loss/total_train_size)
        print()
tests.test_train_nn(train_nn)


def run():
    num_classes = 2
    image_shape = (160, 576)
    data_dir = './data'
    runs_dir = './runs'
    tests.test_for_kitti_dataset(data_dir)

    # Download pretrained vgg model
    helper.maybe_download_pretrained_vgg(data_dir)

    # OPTIONAL: Train and Inference on the cityscapes dataset instead of the Kitti dataset.
    # You'll need a GPU with at least 10 teraFLOPS to train on.
    #  https://www.cityscapes-dataset.com/

    # Hyper Parameters
    EPOCHS = 20 #instead of 20
    BATCH_SIZE = 5 #instead of 5
    L_RATE = 0.0005 #instead of 0.001

    with tf.Session() as sess:
        # Path to vgg model
        vgg_path = os.path.join(data_dir, 'vgg')
        # Create function to get batches
        get_batches_fn = helper.gen_batch_function(os.path.join(data_dir, 'data_road/training'), image_shape)

        # OPTIONAL: Augment Images for better results
        #  https://datascience.stackexchange.com/questions/5224/how-to-prepare-augment-images-for-neural-network

        # TODO: Build NN using load_vgg, layers, and optimize function
        correct_label = tf.placeholder(tf.int32, [None, None, None, num_classes], name='correct_label')
        #learning_rate = tf.placeholder(tf.float32, name='learning_rate')
        learning_rate = L_RATE

        vgg_input, vgg_keep_prob, vgg_layer3, vgg_layer4, vgg_layer7 = load_vgg(sess, vgg_path)
        layer_output = layers(vgg_layer3, vgg_layer4, vgg_layer7, num_classes)
        logits, training_operation, cross_entropy_loss = optimize(layer_output, correct_label, learning_rate, num_classes)

        # TODO: Train NN using the train_nn function
        train_nn(sess, EPOCHS, BATCH_SIZE, get_batches_fn, training_operation, cross_entropy_loss, vgg_input, correct_label, vgg_keep_prob, learning_rate)

        # TODO: Save inference data using helper.save_inference_samples
        #  helper.save_inference_samples(runs_dir, data_dir, sess, image_shape, logits, keep_prob, input_image)
        helper.save_inference_samples(runs_dir, data_dir, sess, image_shape, logits, vgg_keep_prob, vgg_input)


        # OPTIONAL: Apply the trained model to a video


if __name__ == '__main__':
    run()
