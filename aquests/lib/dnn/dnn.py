import tensorflow as tf
import numpy as np
import sys
import os, shutil
import random
from aquests.lib import pathtool
from . import overfit

class DNN:
    def __init__ (self, gpu_usage = 0, name = None):
        self.gpu = gpu_usage        
        self.name = name
        
        self.graph = tf.Graph ()
        with self.graph.as_default ():
            self.make_place_holders ()        
            self.dropout_rate = tf.placeholder_with_default (tf.constant(0.0), ())        
            self.phase_train = False
            
            self.logits = self.make_logits ()
            self.pred = self.make_pred ()            
            self.saver = tf.train.Saver (tf.global_variables())
            
        self.session = None
        self.writers = {}
        self.overfitwatch = None
        self.summaries_dir = None
        
    def init_session (self):
        if self.gpu:
            self.sess = tf.Session (graph = self.graph, config = tf.ConfigProto(gpu_options=tf.GPUOptions (per_process_gpu_memory_fraction = self.gpu), log_device_placement = False))
        else:
            self.sess = tf.Session(graph = self.graph)            
        self.sess.run (tf.global_variables_initializer())     
    
    def reset_dir (self, target):
        if os.path.exists (target):
            shutil.rmtree (target)
        if not os.path.exists (target):
            os.makedirs (target)
    
    def reset_tensor_board (self, summaries_dir, reset = True):
        self.summaries_dir = summaries_dir
        if reset:
            os.system ('killall tensorboard')
            if tf.gfile.Exists(summaries_dir):
                tf.gfile.DeleteRecursively(summaries_dir)
            tf.gfile.MakeDirs(summaries_dir)
            tf.summary.merge_all()
                     
    def get_writers (self, *writedirs):        
        return [tf.summary.FileWriter(os.path.join (self.summaries_dir, "%s%s" % (self.name and self.name + "-" or "", wd)), self.sess.graph) for wd in writedirs]
    
    def make_writers (self, *writedirs):
        for i, w in enumerate (self.get_writers (*writedirs)):
            self.writers [writedirs [i]] = w
    
    def write_summary (self, writer, epoch, feed_dict, verbose = True):
        summary = tf.Summary()
        output = []
        for k, v in feed_dict.items ():
            if self.name:
                k = "{}:{}".format (self.name, k)
            summary.value.add(tag = k , simple_value = v)
            if isinstance (v, float):
                output.append ("{} {:.7f}".format (k, v))
            else:
                output.append ("{} {}".format (k, v))
                
        self.writers [writer].add_summary(summary, epoch)
        if verbose:
            print ("[%d:%7s] %s" % (epoch, writer, " / ".join (output)))
        
    def restore (self, path, gpu = 0.4):
        if self.name:
            path = os.path.join (path, self.name)        
        
        with self.graph.as_default ():
            self.init_session ()
            self.saver.restore(self.sess, tf.train.latest_checkpoint(path))
        
    def save (self, path, filename = None):
        if self.name:
            path = os.path.join (path, self.name)
            pathtool.mkdir (path)                            
        if filename:
            path = os.path.join (path, filename)            
        
        with self.graph.as_default ():
            self.saver.save(self.sess, path, global_step = self.global_step)
    
    def export (self, version, path, predict_def, inputs, outputs):
        if self.name:
            path = os.path.join (path, self.name)
        
        with self.graph.as_default ():
            tf.app.flags.DEFINE_integer('model_version', version, 'version number of the model.')
            tf.app.flags.DEFINE_string('work_dir', '/tmp', 'Working directory.')
            FLAGS = tf.app.flags.FLAGS
            
            builder = tf.saved_model.builder.SavedModelBuilder("{}/{}/".format (path, version))
            prediction_signature = (
              tf.saved_model.signature_def_utils.build_signature_def(
                  inputs=dict ([(k, tf.saved_model.utils.build_tensor_info (v)) for k,v in inputs.items ()]),
                  outputs=dict ([(k, tf.saved_model.utils.build_tensor_info (v)) for k,v in outputs.items ()]),
                  method_name=tf.saved_model.signature_constants.PREDICT_METHOD_NAME))
            
            builder.add_meta_graph_and_variables(
              self.sess, [tf.saved_model.tag_constants.SERVING],
              signature_def_map = {
                  predict_def: prediction_signature
              }
            )
            builder.save()

    def run (self, *ops, **kargs):
        feed_dict = {}
        for k, v in kargs.items ():
            feed_dict [getattr (self, k)] = v
        return self.sess.run (ops, feed_dict = feed_dict)
    
    def get_best_cost (self):
        return overfitwatch.min_cost
        
    def is_overfit (self, cost, path, filename = None):
        if filename is None:
            filename = "cost-%.7f" % cost
        overfit, lowest = self.overfitwatch.add_cost (cost)        
        if not overfit and lowest:
            self.save (path, filename)            
        return overfit
        
    # make trainable ----------------------------------------------------------
    def trainable (self, start_learning_rate=0.00001, decay_step=3000, decay_rate=0.99, overfit_threshold = 0.02):
        self.overfitwatch = overfit.Overfit (overfit_threshold)
        
        self.start_learning_rate = start_learning_rate
        self.decay_step = decay_step
        self.decay_rate = decay_rate
        self.phase_train = True
        
        with self.graph.as_default ():
            self.global_step = tf.Variable(0, trainable=False)
            self.learning_rate = tf.train.exponential_decay(self.start_learning_rate, self.global_step, self.decay_step, self.decay_rate, staircase=False)
            
            self.cost = self.make_cost ()
            self.accuracy = self.calculate_accuracy ()
            tf.summary.scalar('cost', self.cost)
            tf.summary.scalar('learning_rate', self.learning_rate)   
            
            #optimizer = tf.train.MomentumOptimizer(learning_rate=learning_rate, momentum=0.9).minimize(cost, global_step=global_step)
            self.optimizer = tf.train.AdamOptimizer(learning_rate=self.learning_rate).minimize(self.cost, global_step=self.global_step)
            self.init_session ()  
    
    # layering -------------------------------------------------------------------
    def swish (self, x):
        return tf.nn.sigmoid(x) * x    
    
    def dropout (self, layer):
        return tf.layers.dropout (inputs=layer, rate = self.dropout_rate, training=self.phase_train)
        
    def make_hidden_layer (self, n_input, n_output, activation = tf.nn.relu):
        h1 = tf.layers.dense (inputs = n_input, units = n_output)
        h2 = tf.layers.batch_normalization (h1, momentum = 0.99, training = self.phase_train)
        return self.dropout (activation (h2))
    
    def make_conv_layer (self, n_input, num_filters, sequence_length, filter_size, embedding_size, activation = tf.nn.relu):
        h = tf.layers.conv2d (
            inputs = input_dim,
            filters = num_filters,
            kernel_size = [filter_size, embedding_size],
            padding = "valid",
            activation = activation
        )
        # Maxpooling over the outputs
        pooled = tf.layers.max_pooling2d (
            inputs = h, 
            pool_size = [sequence_length - filter_size + 1, 1], 
            strides = 1,
            padding = 'valid'
        )
        
    # override theses ----------------------------------------------------------            
    def make_logits (self):
        #layer1 = self._make_layer (self.x, n_hidden_1)
        layer2 = self.make_hidden_layer (self.x, n_hidden_2)
        layer3 = self.make_hidden_layer (layer2, n_hidden_3)
        layer4 = self.make_hidden_layer (layer3, n_hidden_4)
        return tf.layers.dense (inputs=layer4, units=n_output)
    
    def make_pred (self):
        return tf.nn.sigmoid (self.logits)
    
    def make_place_holders (self):
        self.x = tf.placeholder ("float", [None, n_input])
        self.y = tf.placeholder ("float", [None, n_output])
    
    def make_cost (self):
        pass
    
    def measure_accuracy (self, preds, xs, ys):
        # filtering predict by org_cd
        matches = []
        for i, pred in enumerate (preds):
            ans_x = self.vectorizer.get_unit_index (pred, xs [i])
            matches.append (int (ans_x == np.argmax (ys [i])))
        return np.mean (matches)
     
    def calculate_accuracy (self):
        pass
    