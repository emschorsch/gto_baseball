#!/usr/bin/env python
# Copyright (C) 2015 Author: Emanuel Schorsch

import unittest



class TestIntegration(unittest.TestCase):
    # TODO: mock out stat_loader so can run this without database loaded
    """
    def testOptimizerSanity(self):
        results = optimizer.optimize('2014', '0917', 2, 5)
        # Tests that the actual number of points the lineup would have scored is
        # possible and not an error.
        assert(10 < results.ix[0]["actual total"] < 220)
        # If the projected lineup total ever falls outside the below range it is
        # most likely a bug
        assert(80 < results.ix[0]["pred total"] < 350)
    """


if __name__ == "__main__":
    unittest.main()
