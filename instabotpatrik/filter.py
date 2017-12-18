import logging
import time
import instabotpatrik


# TODO: refactor like/follow/unfollow delay filters -> Can be single dictionary based class

def _check_if_user_is_fully_known(user):
    if not user.is_fully_known():
        raise instabotpatrik.model.InsufficientInformationException(
            "User %s is not fully known. StrategyFollowBasic can't determine "
            "whether we should follow or not.")


def _log_filter_passed(user, filter_instance):
    """
    :type user: instabotpatrik.model.InstagramUser
    """
    logging.info("User id:%s username:%s passed the filter %s. Based on data filter evaluated: %s",
                 user.instagram_id,
                 user.username,
                 filter_instance.__class__.__name__,
                 filter_instance.get_filter_result_as_string(user)
                 )


def _log_filter_not_passed(user, filter_instance):
    """
    :type user: instabotpatrik.model.InstagramUser
    """
    logging.info("User id:%s username:%s didn't pass the filter %s. Based on data filter evaluated: %s",
                 user.instagram_id,
                 user.username,
                 filter_instance.__class__.__name__,
                 filter_instance.get_filter_result_as_string(user)
                 )


def log_filter_result(pass_method):
    def inner(filter_instance, user):
        passed = pass_method(self=filter_instance, user=user)
        if passed:
            _log_filter_passed(user, filter_instance)
        else:
            _log_filter_not_passed(user, filter_instance)
        return passed

    return inner


class UserFollowsCountFilter:
    def __init__(self, min_follows, max_follows):
        super().__init__()
        self.max_follows = max_follows
        self.min_folows = min_follows

    @log_filter_result
    def passes(self, user):
        """
        :param user: user which should be fully known - should have populated details
        :type user: instabotpatrik.model.InstagramUser
        :rtype: bool
        """
        _check_if_user_is_fully_known(user)
        return self.min_folows < user.detail.count_follows < self.max_follows

    def get_filter_result_as_string(self, user):
        return "Follows min: %d, Follows max: %d, Actual follows: %d" % \
               (self.min_folows, self.max_follows, user.detail.count_follows)


class UserFollowedByCountFilter:
    def __init__(self, min_followed_by, max_followed_by):
        super().__init__()
        self.max_followed_by = max_followed_by
        self.min_followed_by = min_followed_by

    @log_filter_result
    def passes(self, user):
        """
        :param user: user which should be fully known - should have populated details
        :type user: instabotpatrik.model.InstagramUser
        :rtype: bool
        """
        _check_if_user_is_fully_known(user)
        return self.min_followed_by < user.detail.count_followed_by < self.max_followed_by

    def get_filter_result_as_string(self, user):
        return "Followed by min: %d, Followed by max: %d, Actual followed by: %d" % \
               (self.min_followed_by, self.max_followed_by, user.detail.count_followed_by)


class UserNotFollowedByUsFilter:

    @log_filter_result
    def passes(self, user):
        """
        :type user: instabotpatrik.model.InstagramUser
        :rtype: bool
        """
        _check_if_user_is_fully_known(user)
        return user.detail.we_follow_user
        # TODO: we could also figure it out base on folow / unfollow timestamps - that would be necessary in case
        # we started following the user without requesting details of his profile

    def get_filter_result_as_string(self, user):
        return "We follow this user" if user.detail.we_follow_user \
            else "We don't follow this user."


class LastUnfollowFilter:
    def __init__(self, more_than_hours_ago):
        super().__init__()
        self.minimal_delay_sec = 60 * 60 * more_than_hours_ago

    @log_filter_result
    def passes(self, user):
        """
        :type user: instabotpatrik.model.InstagramUser
        :rtype: bool
        """
        if user.bot_data.dt_unfollow is None:
            return True
        else:
            return self._get_seconds_passed(user) > self.minimal_delay_sec

    @staticmethod
    def _get_seconds_passed(user):
        now = instabotpatrik.tools.get_utc_datetime()
        ts = user.bot_data.dt_unfollow
        r = now - ts
        return (instabotpatrik.tools.get_utc_datetime() - user.bot_data.dt_unfollow).seconds

    def get_filter_result_as_string(self, user):
        if user.bot_data.dt_unfollow is None:
            return "There's no unfollow timestmap record."
        else:
            return "Time passed since last unfollow %f. Minimal delay is %f." % (
            self._get_seconds_passed(user), self.minimal_delay_sec)


class LastFollowFilter:
    def __init__(self, more_than_hours_ago):
        super().__init__()
        self.minimal_delay_sec = 60 * 60 * more_than_hours_ago

    @log_filter_result
    def passes(self, user):
        """
        :type user: instabotpatrik.model.InstagramUser
        :rtype: bool
        """
        if user.bot_data.dt_follow is None:
            return True
        else:
            return self._get_seconds_passed(user) > self.minimal_delay_sec

    @staticmethod
    def _get_seconds_passed(user):
        return (instabotpatrik.tools.get_utc_datetime() - user.bot_data.dt_follow).seconds

    def get_filter_result_as_string(self, user):
        if user.bot_data.dt_follow is None:
            return "There's no follow timestmap record."
        else:
            return "Time passed since last follow %f. Minimal delay is %f." % (
                self._get_seconds_passed(user), self.minimal_delay_sec)


class LastLikeFilter:
    def __init__(self, more_than_hours_ago):
        super().__init__()
        self.threshold_sec = 60 * 60 * more_than_hours_ago

    @log_filter_result
    def passes(self, user):
        """
        :type user: instabotpatrik.model.InstagramUser
        :returns: True if it is true that user's media was liked more than threshold. False otherwise
        :rtype: bool
        """
        if user.bot_data.dt_like is None:
            return True
        else:
            return self._get_seconds_passed(user) > self.threshold_sec

    @staticmethod
    def _get_seconds_passed(user):
        return (instabotpatrik.tools.get_utc_datetime() - user.bot_data.dt_like).seconds

    def get_filter_result_as_string(self, user):
        if user.bot_data.dt_like is None:
            return "There's no like timestmap record."
        else:
            return "Time passed since last like %f. Minimal delay is %f." % (
                self._get_seconds_passed(user), self.threshold_sec)
