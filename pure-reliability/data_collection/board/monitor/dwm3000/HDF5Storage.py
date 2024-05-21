import numpy as np
import h5py

class HDF5Storage():
    def __init__(self, filename="diagnostics.hdf5"):
        self.total = 0
        self.filename = filename
        with h5py.File(self.filename,'w') as f:
            # just recreate the file
            pass
        self.buffer = []

    def save_to_buffer(self, data):
        self.buffer.append(data)
        self.total += 1

    def save_buffer_to_file(self):
        with h5py.File(self.filename,'a') as f:
            if self.buffer != []:
                for key in self.buffer[0].keys():
                    element = np.array([d[key] for d in self.buffer])
                    if len(np.shape(element))==1:
                        element = element.reshape(-1,1)
                    self.dataset_append(key, element)
                self.buffer = []

    def dataset_append(self, name, data):
        with h5py.File(self.filename,'a') as f:
            if name not in f:
                f.create_dataset(
                    name,
                    data.shape,
                    data = data,
                    dtype=type(data[0,0]),
                    chunks=True,
                    maxshape=(None, data.shape[1])
                )
            else:
                f[name].resize((f[name].shape[0] + data.shape[0]), axis=0)
                f[name][-data.shape[0]:] = data
    def save_to_file(self, data):
        for key in data:
            self.dataset_append(key, np.array(data[key]).reshape(1,-1))

