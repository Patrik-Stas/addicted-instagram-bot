# -*- coding: utf-8 -*-

from testsUnit.context import instabotpatrik
import unittest


class TestItShouldSelectFromList(unittest.TestCase):
    def test_run(self):
        tags = ["a", "b", "c", "d"]

        def provide_tags():
            return tags

        strategy = instabotpatrik.strategy.StrategyTagSelectionBasic(provide_tags)
        tag1 = strategy.get_tag()
        self.assertTrue(tag1 in tags)


class TestItShouldSeemSelectRandomly(unittest.TestCase):
    def test_run(self):
        def provide_tags():
            return ["a", "b", "c", "d", "e", "f"]

        strategy = instabotpatrik.strategy.StrategyTagSelectionBasic(provide_tags)
        tag_sequence = [strategy.get_tag() for x in range(300)]
        self.assertTrue("a" in tag_sequence)
        self.assertTrue("e" in tag_sequence)


#
# def suite():
#     suite = unittest.TestSuite()
#     suite1 = TestTagSelectionRandom()
#     suite2 = TestTagSelectionRandom2()
#     suite.addTest(suite1, suite2)
#     return suite
#
#
# if __name__ == '__main__':
#     runner = unittest.TextTestRunner()
#     test_suite = suite()
#     runner.run(test_suite)

if __name__ == '__main__':
    unittest.main()
