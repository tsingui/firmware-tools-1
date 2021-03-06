#!/usr/bin/python
# vim:expandtab:autoindent:tabstop=4:shiftwidth=4:filetype=python:
"""
"""

from __future__ import generators

import sys
import os
import unittest

class TestCase(unittest.TestCase):
    def setUp(self):
        if globals().get('firmwaretools'): del(firmwaretools)
        for k in sys.modules.keys():
            if k.startswith("firmwaretools"):
                del(sys.modules[k])

        import firmwaretools.package as package
        pkgA = package.Package(name="pkgA", version="a01", displayname="test pkgA")
        pkgB = package.Package(name="pkgC", version="a02", displayname="test pkgC")
        pkgC = package.Package(name="pkgC", version="a03", displayname="test pkgC")

        self.inventory = {}
        self.inventory['pkgA'] = pkgA
        self.inventory['pkgB'] = pkgB
        self.inventory['pkgC'] = pkgC

    def tearDown(self):
        if globals().get('firmwaretools'): del(firmwaretools)
        for k in sys.modules.keys():
            if k.startswith("firmwaretools"):
                del(sys.modules[k])

    def testExist(self):
        import firmwaretools.dep_parser as dep_parser
        s = "pkgA"
        d = dep_parser.DepParser(s, self.inventory, {})
        self.assertEquals(1, d.depPass)

    def testExist2(self):
        import firmwaretools.dep_parser as dep_parser
        tests = [ ("exist", "pkgA"),
            ("gt",  "pkgA > a00"),
            ("ge1", "pkgA >= a00"),
            ("ge2", "pkgA >= a01"),
            ("eq",  "pkgA == a01"),
            ("le1", "pkgA <= a01"),
            ("le2", "pkgA <= a02"),
            ("lt",  "pkgA < a02"),
            ("exist_gt", "pkgA, pkgB > a01"),
            ("exist_gt_exist", "pkgA, pkgB > a01, pkgC"), ]

        for name, testStr in tests:
            d = dep_parser.DepParser(testStr, self.inventory, {})
            self.assertEquals(1, d.depPass)

    def testExist3(self):
        import firmwaretools.dep_parser as dep_parser
        tests = [ ("exist", "pkgD"),
            ("gt",  "pkgA > a01"),
            ("ge1", "pkgA >= a02"),
            ("ge2", "pkgA >= a03"),
            ("eq",  "pkgA == a02"),
            ("le1", "pkgA <= a00"),
            ("lt",  "pkgA < a01"),
            ("exist_gt", "pkgA, pkgB > a01, pkgD"),
            ("exist_gt_exist", "pkgA, pkgB < a01, pkgC"), ]

        for name, testStr in tests:
            d = dep_parser.DepParser(testStr, self.inventory, {})
            self.assertEquals(0, d.depPass)






if __name__ == "__main__":
    import test.TestLib
    sys.exit(not test.TestLib.runTests( [TestCase] ))
