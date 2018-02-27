import numpy as np

class Vector:
    def __init__ (self, items):
        self._origin = items
        self._set = isinstance (self._origin, (list, tuple)) and list (set (self._origin)) or list (self._origin.keys ())
        self._set.sort ()
        self._indexes = {}
        for idx, item in enumerate (self._set):
            self._indexes [item] = idx
        self._items = dict ([(v, k) for k, v in self._indexes.items ()])        
    
    def __getitem__ (self, index):
        return self.item (index) 
        
    def info (self, item):
        return self._origin [item] 
    
    def __len__ (self):
        return len (self._set)
    
    def index (self, item):
        return self._indexes [item]
    
    def item (self, index):
        return self._items [index]
    
    def items (selfself, index):
        return self._set
    
    def top_k (self, arr, k = 1):
        items = []         
        for idx in np.argsort (arr)[::-1][:k]:
            items.append (self._items [idx])
        return items
    
    def setval (self, items, value = 1.0, type = np.float, prefix = None):
        arr = np.zeros (len (self._set)).astype (type)
        if not isinstance (items, (dict, list, tuple)):
            items = [items]
        for item in items:
            tid = self._indexes.get (item, -1)
            if tid == -1:
                continue    
            arr [self._indexes [item]] = 1
            
        if prefix is not None:
            return np.concatenate ([prefix, arr])
        else:
            return arr
        
    def setone (self, items, type = np.float, prefix = None):
        return self.setval (items, 1.0, type, prefix)


if __name__ == "__main__":    
    v = Vector (["a", "b", "c", "d", "e"])
    base = v.one (["c", "e"])
    
    v = Vector (["a", "b", "c", "d", "e"])
    print (v.one (["c", "e"], base = base))
    
    
    