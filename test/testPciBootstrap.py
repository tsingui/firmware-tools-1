#!/usr/bin/python2
# vim:expandtab:autoindent:tabstop=4:shiftwidth=4:filetype=python:
"""
"""

from __future__ import generators

import sys
import unittest
import ConfigParser

class TestCase(unittest.TestCase):
    def setUp(self):
        pass
    
    def tearDown(self):
        pass

    def testBootstrapInventory(self):
        # set up unit test mode
        module = __import__("bootstrap_pci", globals(),  locals(), [])
        module.unit_test_mode=1

        # manually setup fake config file
        ini = ConfigParser.ConfigParser()
        ini.add_section("bootstrap_pci")
        ini.set("bootstrap_pci", "bootstrap_inventory_plugin", "bootstrap_pci")

        # run bootstrap and compare.
        import clifuncs
        index = 0
        for pkg in clifuncs.runBootstrapInventory(ini):
            self.assertEqual( module.mockExpectedOutput.split("\n")[index], str(pkg) )
            index = index + 1

        # ensure it actually ran.
        self.assertEqual(index, len(module.mockExpectedOutput.split("\n")))
        

if __name__ == "__main__":
    import test.TestLib
    sys.exit(not test.TestLib.runTests( [TestCase] ))
