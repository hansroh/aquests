import tensorflow as tf


def adam (cost, learning_rate, global_step):
    return tf.train.AdamOptimizer (learning_rate).minimize (cost, global_step = global_step)

def mometum (cost, learning_rate, global_step, mometum = 0.99):
    return tf.train.MomentumOptimizer (learning_rate, mometum).minimize (cost, global_step = global_step)

def rmsprob (cost, learning_rate, global_step, decay = 0.9, mometum = 0.0, epsilon = 1e-10):
    return tf.train.RMSPropOptimizer (learning_rate, decay, momentum, epsilon).minimize(cost, global_step = global_step)

def clip (cost, learning_rate, global_step, min_, max_):
    train_op = tf.train.AdamOptimizer (learning_rate = learning_rate)
    gradients = train_op.compute_gradients (cost)
    capped_gradients = [(tf.clip_by_value (grad, min_, max_), var) for grad, var in gradients]
    return train_op.apply_gradients (capped_gradients, global_step = global_step)
