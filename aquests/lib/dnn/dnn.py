import tensorflow as tf
import numpy as np
import sys
import os, shutil
import random
from aquests.lib import pathtool
from . import overfit, optimizers

class DNN:
    def __init__ (self, gpu_usage = 0, name = None):
        self.gpu = gpu_usage        
        self.name = name
        
        self.graph = tf.Graph ()
        with self.graph.as_default ():
            self.make_default_place_holders ()
            self.make_place_holders ()        
            self.dropout_rate = tf.placeholder_with_default (tf.constant(0.0), ())        
            self.phase_train = False
            
            self.logits = self.make_logits ()
            self.pred = self.make_pred ()            
            self.saver = tf.train.Saver (tf.global_variables())
            
        self.sess = None
        self.writers = {}
        self.overfitwatch = None
        self.overfitted = False
        self.summaries_dir = None
        self.verbose = True
        self.filter_func = None
        
    def set_filter (self, func):
        self.filter_func = func
    
    def filter (self, ys, *args):
        is_no_x = True
        xs = None
        if args:
            is_no_x = False        
            xs = args [0]
             
        if self.filter_func:
            ys, xs = self.filter_func (ys, xs)
        if is_no_x:
            return ys
        return ys, xs        
        
    def turn_off_verbose (self):
        self.verbose = False
            
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
            tf.summary.merge_all ()
                     
    def get_writers (self, *writedirs):        
        return [tf.summary.FileWriter(os.path.join (self.summaries_dir, "%s%s" % (self.name and self.name.strip () + "-" or "", wd)), self.sess.graph) for wd in writedirs]
    
    def make_writers (self, *writedirs):
        for i, w in enumerate (self.get_writers (*writedirs)):
            self.writers [writedirs [i]] = w
    
    def get_epoch (self):
        with self.sess.as_default ():
            return self.global_step.eval ()
                
    def write_summary (self, writer, feed_dict, verbose = True):
        if writer not in self.writers:
            return
        
        summary = tf.Summary()
        output = []
        for k, v in feed_dict.items ():
            if self.name:
                k = "{}:{}".format (self.name, k)
            summary.value.add(tag = k , simple_value = v)
            if isinstance (v, (float, np.float64, np.float32)):
                output.append ("{} {:.7f}".format (k, v))
            elif isinstance (v, (int, np.int64, np.int32)):
                output.append ("{} {:04d}".format (k, v))    
            else:
                output.append ("{} {}".format (k, v))        
        
        if self.overfitted:
            output.append ("Overfitted %s" % self.overfitted)
        
        epoch = self.get_epoch ()
        self.writers [writer].add_summary(summary, epoch)
        if verbose and self.verbose:
            print ("[%d:%7s] %s" % (epoch, writer, " | ".join (output)))
        
    def restore (self, path):
        if self.name:
            path = os.path.join (path, self.name.strip ())        

        with self.graph.as_default ():
            self.init_session ()
            self.saver.restore(self.sess, tf.train.latest_checkpoint(path))
        
    def save (self, path, filename = None):
        if self.name:
            path = os.path.join (path, self.name.strip ())
            pathtool.mkdir (path)                            
        if filename:
            path = os.path.join (path, filename)            
        
        with self.graph.as_default ():
            self.saver.save(self.sess, path, global_step = self.global_step)
    
    def get_latest (self, path):    
        if not os.listdir (path):
            return 0
        return max ([int (ver) for ver in os.listdir (path) if ver.isdigit () and os.path.isdir (os.path.join (path, ver))])    

    def export (self, path, predict_def, inputs, outputs):
        if self.name:
            path = os.path.join (path, self.name.strip ())
        pathtool.mkdir (path)
        version = self.get_latest (path) + 1
        
        with self.graph.as_default ():
            #tf.app.flags.DEFINE_integer('model_version', version, 'version number of the model.')
            #tf.app.flags.DEFINE_string('work_dir', '/tmp', 'Working directory.')
            #FLAGS = tf.app.flags.FLAGS
            
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
        return version    

    def run (self, *ops, **kargs):
        if "y" in kargs:
            kargs ["y"], kargs ["x"] = self.filter (kargs ["y"], kargs ["x"])
            if "n_sample" in kargs:
                kargs ["n_sample"] = len (kargs ["y"])
                            
        feed_dict = {}
        for k, v in kargs.items ():
            feed_dict [getattr (self, k)] = v
        return self.sess.run (ops, feed_dict = feed_dict)
    
    def get_best_cost (self):
        return overfitwatch.min_cost
        
    def is_overfit (self, cost, path, filename = None):
        if filename is None:
            filename = "cost-%.7f" % cost
        self.overfitted, lowest = self.overfitwatch.add_cost (cost)        
        if not self.overfitted and lowest:
            self.save (path, filename)            
        return self.overfitted
    
    def eval (self, tensor):
        with self.sess.as_default ():
            return tensor.eval ()
            
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
            self.optimizer = self.make_optimizer ()
            self.init_session ()  
    
    # layering -------------------------------------------------------------------
    def dropout (self, layer, dropout = True):
        if not dropout:
            return layer
        return tf.layers.dropout (inputs=layer, rate = self.dropout_rate, training=self.phase_train)    
    
    def make_lstm (self, n_input, seq_len, n_channels, hidden_size, lstm_layers = 1, dynamic = True):
        # hidden_size larger than n_channels
        try:
            rnn = tf.nn.rnn_cell
            type_rnn = dynamic and tf.nn.dynamic_rnn or tf.nn.static_rnn                    
        except AttributeError:
            rnn = tf.contrib.rnn
            type_rnn = dynamic and rnn.dynamic_rnn or rnn.static_rnn
        
        cells = []
        for i in range (lstm_layers):
            lstm = rnn.BasicLSTMCell (hidden_size)
            drop = rnn.DropoutWrapper (lstm, output_keep_prob = 1.0 - self.dropout_rate)
            cells.append (drop)
            
        cell = rnn.MultiRNNCell (cells)
        initial_state = cell.zero_state (self.n_sample, tf.float32)
        
        # transform time major form 
        lstm_in = tf.transpose (n_input, [1, 0, 2])
        if not dynamic:            
            lstm_in = tf.reshape (lstm_in, [-1, n_channels])
            lstm_in = tf.layers.dense (lstm_in, hidden_size)
            lstm_in = tf.split (lstm_in, seq_len, 0)
            output, final_state = type_rnn (cell, lstm_in, dtype = tf.float32, initial_state = initial_state)
        else:            
            output, final_state = type_rnn (cell, lstm_in, time_major = True, dtype = tf.float32, initial_state = initial_state)
                    
        return output
    
    def make_fc_layer (self, outputs, n_output):
        return tf.reshape (outputs, [-1, n_output])
    
    def make_sequencial_layer (self, outputs, hidden_size, seq_len, n_output):
        # outputs is rnn outputs
        fc = self.make_fc_layer (outputs, [-1, hidden_size])
        outputs = tf.layers.dense (fc, n_output, activation = None)
        return tf.reshape (outputs, [self.n_sample, seq_len, n_output])
        
    def make_hidden_layer (self, n_input, n_output, activation = None, dropout = True):
        h1 = tf.layers.dense (inputs = n_input, units = n_output)
        h2 = tf.layers.batch_normalization (h1, momentum = 0.99, training = self.phase_train)
        if activation is not None:
            h2 = activation (h2)        
        return self.dropout (h2, dropout)        
    
    def make_conv1d_layer (self, n_input, filters = 6, activation = None,  padding = "same", dropout = True):
        # decreased to half
        # (128, filters) -> (64, filters) -> (32, filters)
        conv = tf.layers.conv1d (inputs = n_input, filters = filters, kernel_size = 2, strides = 1, padding = padding, activation = activation)
        maxp = tf.layers.max_pooling1d (inputs = conv, pool_size = 2, strides = 2, padding = padding)
        return self.dropout (maxp, dropout)
        
    def make_conv2d_layer (self, n_input, filters, kernel_size = (4, 4), pool_size = (2, 2), activation = None, padding = "same", dropout = True):
        conv = tf.layers.conv2d (inputs = n_input, filters = filters, kernel_size = kernel_size, strides = 1, padding = padding, activation = activation)
        maxp = tf.layers.max_pooling2d (inputs = conv, pool_size = pool_size, strides = pool_size [0], padding = padding)
        return self.dropout (maxp, dropout)
    
    # helpers ------------------------------------------------------------------
    def swish (self, x):
        return tf.nn.sigmoid(x) * x
    
    def optimizer (self, name = 'adam', *args, **karg):
        return getattr (optimizers, name) (self.cost, self.learning_rate, self.global_step, *args, **karg)
    
    # override theses ----------------------------------------------------------            
    def make_optimizer (self):
        return self.optimizer ("adam")
    
    get_optimizer = make_optimizer
    
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
    
    def make_default_place_holders (self):    
        self.n_sample = tf.placeholder ("int32", [])
    
    def make_cost (self):
        pass
    
    def calculate_complex_accuracy (self, preds, ys, *args, **karg):
        ys = self.filter (ys)
    measure_accuracy = calculate_complex_accuracy
     
    def calculate_accuracy (self):
        pass
    