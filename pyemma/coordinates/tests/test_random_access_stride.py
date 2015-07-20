import os
import tempfile
import unittest
from unittest import TestCase
import numpy as np
import pyemma.coordinates.api as coor
import pkg_resources
import mdtraj


class TestRandomAccessStride(TestCase):
    def setUp(self):
        self.dim = 5
        self.data = [np.random.random((100, self.dim)),
                     np.random.random((1, self.dim)),
                     np.random.random((2, self.dim))]
        self.stride = {0: [1, 3, 3, 5, 6, 7], 2: [1,1]}
        self.stride2 = {2: [0]}

    def test_data_in_memory_random_access(self):
        # access with a chunk_size that is larger than the largest index list of stride
        data_in_memory = coor.source(self.data, chunk_size=10)
        out1 = data_in_memory.get_output(stride=self.stride)

        # access with a chunk_size that is smaller than the largest index list of stride
        data_in_memory = coor.source(self.data, chunk_size=1)
        out2 = data_in_memory.get_output(stride=self.stride)

        # access in full trajectory mode
        data_in_memory = coor.source(self.data, chunk_size=0)
        out3 = data_in_memory.get_output(stride=self.stride)

        for idx in self.stride.keys():
            np.testing.assert_array_almost_equal(self.data[idx][np.array(self.stride[idx])], out1[idx])
            np.testing.assert_array_almost_equal(out1[idx], out2[idx])
            np.testing.assert_array_almost_equal(out2[idx], out3[idx])

    def test_data_in_memory_without_first_two_trajs(self):
        data_in_memory = coor.source(self.data, chunk_size=10)
        out = data_in_memory.get_output(stride=self.stride2)
        np.testing.assert_array_almost_equal(out[2], self.data[2][np.array(self.stride2[2])])

    def test_numpy_filereader_random_access(self):
        tmpfiles = [tempfile.mktemp(suffix='.npy') for _ in xrange(0, len(self.data))]
        try:
            for idx, tmp in enumerate(tmpfiles):
                np.save(tmp, self.data[idx])
            # large enough chunk size
            np_fr = coor.source(tmpfiles, chunk_size=10)
            out1 = np_fr.get_output(stride=self.stride)

            # small chunk size
            np_fr = coor.source(tmpfiles, chunk_size=1)
            out2 = np_fr.get_output(stride=self.stride)

            # full traj mode
            np_fr = coor.source(tmpfiles, chunk_size=0)
            out3 = np_fr.get_output(stride=self.stride)

            for idx in self.stride.keys():
                np.testing.assert_array_almost_equal(self.data[idx][np.array(self.stride[idx])], out1[idx])
                np.testing.assert_array_almost_equal(out1[idx], out2[idx])
                np.testing.assert_array_almost_equal(out2[idx], out3[idx])

        finally:
            for tmp in tmpfiles:
                try:
                    os.unlink(tmp)
                except EnvironmentError:
                    pass

    def test_transformer_iterator_random_access(self):
        kmeans = coor.cluster_kmeans(self.data, k=2)
        kmeans.in_memory = True

        for cs in xrange(1, 5):
            kmeans.chunksize = cs
            ref_stride = {0: 0, 1: 0, 2: 0}
            for x in kmeans.iterator(stride=self.stride):
                ref_stride[x[0]] += len(x[1])
            for key in ref_stride.keys():
                expected = (len(self.stride[key]) if key in self.stride.keys() else 0)
                assert ref_stride[key] == expected, \
                    "Expected to get exactly %s elements of trajectory %s, but got %s for chunksize=%s" \
                    % (expected, key, ref_stride[key], cs)

    def test_feature_reader_random_access(self):
        from pyemma.coordinates.tests.test_featurereader import create_traj
        topfile = pkg_resources.resource_filename('pyemma.coordinates.tests.test_featurereader', 'data/test.pdb')
        trajfiles = []
        for _ in range(3):
            f, _, _ = create_traj(topfile)
            trajfiles.append(f)
        try:
            source = coor.source(trajfiles, top=topfile)
            source.chunksize = 2

            out = source.get_output(stride=self.stride)
            for i, coords in enumerate(out):
                if i in self.stride.keys():
                    traj = mdtraj.load(trajfiles[i], top=topfile)
                    np.testing.assert_equal(coords, traj.xyz[np.array(self.stride[i])].reshape(-1, 9))
        finally:
            for t in trajfiles:
                try:
                    os.unlink(t)
                except EnvironmentError:
                    pass


if __name__ == '__main__':
    unittest.main()
