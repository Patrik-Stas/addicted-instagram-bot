from testsUnit.context import instabotpatrik
import unittest
import time


class ItShouldAllowActionAfterTimePasses(unittest.TestCase):
    def runTest(self):
        manager = instabotpatrik.tools.ActionManager()
        manager.allow_action_after_seconds("unfollow", 0.5)
        time.sleep(0.5)
        self.assertTrue(manager.is_action_allowed_now("unfollow"))


class ItShoulNotdAllowActionBeforeTimePasses(unittest.TestCase):
    def runTest(self):
        manager = instabotpatrik.tools.ActionManager()
        manager.allow_action_after_seconds("unfollow", 0.5)
        self.assertFalse(manager.is_action_allowed_now("unfollow"))


class ItShouldCalculateMinimalWaitingTime(unittest.TestCase):
    def runTest(self):
        manager = instabotpatrik.tools.ActionManager()
        manager.allow_action_after_seconds("liking_session", 3)
        manager.allow_action_after_seconds("unfollow", 4)
        time.sleep(1)
        self.assertAlmostEqual(2, manager.time_left_until_some_action_possible()['sec_left'], delta=0.1)
        self.assertEqual("liking_session", manager.time_left_until_some_action_possible()['action_name'])
