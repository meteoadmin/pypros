import unittest

import numpy

from osgeo import gdal, osr
from pypros.pros import PyPros


class TestCalculateRos(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data_format = {'vars_files': ['tair', 'tdew', 'dem']}
        cls.variables_file = ['/tmp/tair.tif',
                              '/tmp/tdew.tif',
                              '/tmp/dem.tif']
        cls.method = 'ks'
        cls.threshold = None

        size = [3, 3]
        tair = numpy.ones(size)
        tdew = numpy.ones(size)
        dem = numpy.ones(size)

        for i in range(3):
            tair[0][i] = 20
            tdew[0][i] = 20
            tair[1][i] = 2
            tdew[1][i] = 0
            tair[2][i] = -1
            tdew[2][i] = -1
            dem[0][i] = 0
            dem[1][i] = 1500
            dem[2][i] = 3000

        fields = [tair, tdew, dem]

        for i in range(len(fields)):
            driver = gdal.GetDriverByName('GTiff')
            d_s = driver.Create(cls.variables_file[i], size[1], size[0], 1,
                                gdal.GDT_Float32)

            d_s.GetRasterBand(1).WriteArray(fields[i])
            d_s.SetGeoTransform((0, 100, 0, 200, 0, -100))

            proj = osr.SpatialReference()
            proj.ImportFromEPSG(25831)

            d_s.SetProjection(proj.ExportToWkt())

            d_s = None

        cls.method = 'ks'

    def test_init(self):
        inst = PyPros(self.variables_file, self.method, self.threshold,
                      self.data_format)
        self.assertEqual(inst.result.shape, (3, 3))

        inst.save_file(inst.result, "/tmp/out.tiff")

    def test_init_wrong_size(self):
        size = [1, 1]
        wrong = numpy.ones(size)
        wrong_file = '/tmp/wrong.tif'
        driver = gdal.GetDriverByName('GTiff')
        d_s = driver.Create(wrong_file, size[1], size[0], 1,
                            gdal.GDT_Float32)

        d_s.GetRasterBand(1).WriteArray(wrong)
        d_s.SetGeoTransform((0, 100, 0, 200, 0, -100))

        proj = osr.SpatialReference()
        proj.ImportFromEPSG(25831)

        d_s.SetProjection(proj.ExportToWkt())

        d_s = None

        variables_file = ['/tmp/tair.tif', wrong_file]
        with self.assertRaises(ValueError) as cm:
            PyPros(variables_file, self.method, self.threshold,
                   self.data_format)
        self.assertEqual(
            'Variables fields must have the same shape.',
            str(cm.exception))

    def test_init_different_methods(self):
        inst = PyPros(self.variables_file, 'ks', self.threshold,
                      self.data_format)
        self.assertEqual(inst.result.shape, (3, 3))

        inst = PyPros(self.variables_file, 'single_tw', 1.5,
                      self.data_format)
        self.assertEqual(inst.result.shape, (3, 3))

        inst = PyPros(self.variables_file, 'single_ta', 1.0,
                      self.data_format)
        self.assertEqual(inst.result.shape, (3, 3))

        inst = PyPros(self.variables_file, 'linear_tr', [0, 3],
                      self.data_format)
        self.assertEqual(inst.result.shape, (3, 3))

        inst = PyPros(self.variables_file, 'dual_ta', [0, 3],
                      self.data_format)
        self.assertEqual(inst.result.shape, (3, 3))

        inst = PyPros(self.variables_file, 'dual_tw', [0, 3],
                      self.data_format)
        self.assertEqual(inst.result.shape, (3, 3))

    def test_init_twet_without_dem(self):
        variables_file = ['/tmp/tair.tif', '/tmp/tdew.tif']
        data_format = {'vars_files': ['tair', 'tdew']}
        try:
            PyPros(variables_file, 'single_tw', 1.5,
                   data_format)
        except Exception as cm:
            self.assertEqual('Since no DEM is supplied, wet bulb ' +
                             'temperature calculations will assume ' +
                             'a constant pressure of 1013.25 hPa.',
                             str(cm.exception))

    def test_init_different_methods_wrong(self):

        with self.assertRaises(ValueError) as cm:
            PyPros(self.variables_file, 'single_tw', '1',
                   self.data_format)
        self.assertEqual(
            'The threshold for the method {} must be a float',
            str(cm.exception))

        with self.assertRaises(ValueError) as cm:
            PyPros(self.variables_file, 'single_ta', '1.5',
                   self.data_format)
        self.assertEqual(
            'The threshold for the method {} must be a float',
            str(cm.exception))

        with self.assertRaises(ValueError) as cm:
            PyPros(self.variables_file, 'linear_tr', [3],
                   self.data_format)
        self.assertEqual(
            'The thresholds for the method {} must be a list/tuple' +
            ' of length two', str(cm.exception))

        with self.assertRaises(ValueError) as cm:
            PyPros(self.variables_file, 'dual_tw', [3],
                   self.data_format)
        self.assertEqual(
            'The thresholds for the method {} must be a list/tuple' +
            ' of length two', str(cm.exception))

        with self.assertRaises(ValueError) as cm:
            PyPros(self.variables_file, 'dual_ta', [3],
                   self.data_format)
        self.assertEqual(
            'The thresholds for the method {} must be a list/tuple' +
            ' of length two', str(cm.exception))

    def test_refl_mask(self):

        inst = PyPros(self.variables_file, 'ks', self.threshold,
                      self.data_format)

        refl = numpy.ones((3, 3))

        refl_values = [0.2, 2, 6, 12, 16, 26]
        for i in range(3):
            refl[0][i] = refl_values[i]
            refl[1][i] = refl_values[i]
            refl[2][i] = refl_values[i]

        pros_masked = inst.refl_mask(refl)

        # rain
        for i in range(1, 3):
            self.assertEqual(pros_masked[0][i], i)
        # sleet
        for i in range(1, 3):
            self.assertEqual(pros_masked[1][i], 5 + i)
        # snow
        for i in range(1, 3):
            self.assertEqual(pros_masked[2][i], 10 + i)

        inst = PyPros(self.variables_file, 'single_tw', 1.5,
                      self.data_format)
        pros_masked = inst.refl_mask(refl)

        # rain
        for i in range(1, 3):
            self.assertEqual(pros_masked[0][i], i)
        # snow
        for i in range(1, 3):
            self.assertEqual(pros_masked[2][i], 10 + i)

        inst = PyPros(self.variables_file, 'single_ta', 1.0,
                      self.data_format)
        pros_masked = inst.refl_mask(refl)

        # rain
        for i in range(1, 3):
            self.assertEqual(pros_masked[0][i], i)
        # snow
        for i in range(1, 3):
            self.assertEqual(pros_masked[2][i], 10 + i)

        inst = PyPros(self.variables_file, 'linear_tr', [0, 3],
                      self.data_format)
        pros_masked = inst.refl_mask(refl)

        # rain
        for i in range(1, 3):
            self.assertEqual(pros_masked[0][i], i)
        # sleet
        for i in range(1, 3):
            self.assertEqual(pros_masked[1][i], 5 + i)
        # snow
        for i in range(1, 3):
            self.assertEqual(pros_masked[2][i], 10 + i)

        inst = PyPros(self.variables_file, 'dual_ta', [0, 3],
                      self.data_format)
        pros_masked = inst.refl_mask(refl)

        # rain
        for i in range(1, 3):
            self.assertEqual(pros_masked[0][i], i)
        # sleet
        for i in range(1, 3):
            self.assertEqual(pros_masked[1][i], 5 + i)
        # snow
        for i in range(1, 3):
            self.assertEqual(pros_masked[2][i], 10 + i)

        inst = PyPros(self.variables_file, 'dual_tw', [0, 3],
                      self.data_format)
        pros_masked = inst.refl_mask(refl)

        # rain
        for i in range(1, 3):
            self.assertEqual(pros_masked[0][i], i)
        # sleet
        for i in range(1, 3):
            self.assertEqual(pros_masked[1][i], 5 + i)
        # snow
        for i in range(1, 3):
            self.assertEqual(pros_masked[2][i], 10 + i)

    def test_refl_mask_wrong(self):
        variables_file = ['/tmp/tair.tif', '/tmp/tdew.tif']
        data_format = {'vars_files': ['tair', 'tdew']}

        refl = numpy.ones((1, 1))

        with self.assertRaises(IndexError) as cm:
            inst = PyPros(variables_file, 'single_ta', 1.5,
                          data_format)
            inst.refl_mask(refl)
        self.assertEqual('Variables fields must have the same shape.',
                         str(cm.exception))


if __name__ == '__main__':
    unittest.main()
