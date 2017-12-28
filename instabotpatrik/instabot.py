#!/usr/bin/env python
# -*- coding: utf-8 -*-
import datetime
import logging
import instabotpatrik
import random


# TODO : Limit cap middle layer
# TODO: Extract fetching media out - all I need is interface: get me this many media. I don't need to care where are
# those media coming from for now
# TODO: Some generalized scheduler class maybe?

# comment: I ideally on instabot layer I would really just say what actions/workflows I wanna do and how often I wanna
# do them. Groovy DSL for that? Python DSL? (programmable bot, but also with UI ...aiguuuu, total killer)

# TODO: annotations for scheduling... anotate method with @allowAfter(action='like', sec=300) ... and if the like was
# succesfull, then this annotation will asure to setup action manager to allow like only after 300 seconds
class InstaBot:

    def __init__(self,
                 media_controller,
                 user_controller,
                 login_controller,
                 strategy_tag_selection):
        """
        :param media_controller:
        :type media_controller: instabotpatrik.core.MediaController
        :param user_controller:
        :type user_controller: instabotpatrik.core.UserController
        :param login_controller:
        :type login_controller: instabotpatrik.core.AccountController
        """

        self.media_controller = media_controller
        self.user_controller = user_controller
        self.login_controller = login_controller

        self.bot_start = datetime.datetime.now()
        self.strategy_tag_selection = strategy_tag_selection

        # self.follow_per_day_cap = 150
        self.unfollow_per_day_cap = 150
        self.lfs_per_day_cap = 100  # lfs = like-follow-session

        self.time_in_day = 24 * 60 * 60
        self.ban_sleep_time_sec = 2 * 60 * 60  # how long sleep if we get non 2xx response

        self.lfs_delay_sec = self.time_in_day / self.lfs_per_day_cap
        self.unfollow_delay_sec = self.time_in_day / self.unfollow_per_day_cap

        self.action_manager = instabotpatrik.tools.ActionManager()
        self.unfollow_workflow = instabotpatrik.workflow.UnfollowWorkflow(user_controller=self.user_controller)
        self.lfs_workflow = instabotpatrik.workflow.LfsWorkflow(user_controller=self.user_controller,
                                                                media_controller=self.media_controller)

        self.select_ratio = 0.55

        logging.info("Created instabot. Unfollows per day:%d, LFS per day:%d.", self.unfollow_delay_sec,
                     self.lfs_per_day_cap)
        logging.info("Unfollow interval sec:%d, LFS interval sec:%d. ", self.unfollow_delay_sec, self.lfs_delay_sec)
        logging.info("Sleep on non 2xx response: %d sec.", self.ban_sleep_time_sec)
        logging.info("Ratio of randomly selected media batch for tag: %f.", self.select_ratio)

        self.current_tag = None
        self._stopped = False

        # self.like_delay_sec = self.time_in_day / self.like_per_day_cap    part of LFS
        # self.follow_delay_sec = self.time_in_day / self.follow_per_day_cap  part of LFS

    def schedule_and_execute_actions_for_medias(self, medias):
        """
        :param medias:
        :type medias: list of instabotpatrik.model.InstagramMedia
        :return:
        """
        while len(medias) > 0 and self._stopped is False:
            try:
                logging.info("[INSTABOT] Handle media one by one by one: Some action should be possible now.")

                # ----- IF SCHEDULED: UNFOLLOW ------
                if self.action_manager.is_action_allowed_now("unfollow"):
                    logging.info("[INSTABOT] Going to unfollow someone.")
                    try:
                        self.unfollow_workflow.run()
                    finally:
                        self.action_manager.allow_action_after_seconds('unfollow', self.unfollow_delay_sec)

                # ----- IF SCHEDULED: LIKING SESSIONS------
                if self.action_manager.is_action_allowed_now("liking_session"):
                    media = medias.pop()
                    logging.info("[INSTABOT] Going to check if we can do LFS on media %s", media.shortcode)
                    media_owner = self.user_controller.get_media_owner(media_shortcode=media.shortcode,
                                                                       asure_fresh_data=True)  # explore users profile
                    if self.lfs_workflow.is_approved_for_lfs(media_owner):
                        logging.info("[INSTABOT] Starting LFS on owner of media %s", media.shortcode)
                        try:
                            self.lfs_workflow.run(media, media_owner)
                        finally:
                            self.action_manager.allow_action_after_seconds('liking_session', self.unfollow_delay_sec)

                # ----- WAIT TILL NEXT ACTION------
                info = self.action_manager.seconds_left_until_some_action_possible()
                logging.info("Next possible action will be %s in %d seconds", info['action_name'], info['sec_left'])
                logging.info("Time left till next liking_session %d"
                             % self.action_manager.seconds_left_until_action_possible("liking_session"))
                logging.info("Time left till next unfollow %d"
                             % self.action_manager.seconds_left_until_action_possible("unfollow"))
                instabotpatrik.tools.go_sleep(duration_sec=info['sec_left'] + 3, plusminus=3)

            except instabotpatrik.client.InstagramResponseException as e:
                raise e
            except Exception as e:
                logging.error(e, exc_info=True)
                logging.error("Something went wrong. Will sleep 60 seconds")
                instabotpatrik.tools.go_sleep(duration_sec=60, plusminus=1)

    def run(self):
        logging.info("[INSTABOT] Starting bot with following configuration:")
        logging.info("[INSTABOT] Daily cap of LFS count:%d", self.lfs_per_day_cap)
        logging.info("[INSTABOT] Daily cap for unfollow count:%d", self.unfollow_per_day_cap)

        self.login_controller.login()

        while not self._stopped:
            try:
                self.current_tag = self.strategy_tag_selection.get_tag()
                logging.info("[INSTABOT] Starting main loop. Selected tag: %s", self.current_tag)
                our_username = self.login_controller.get_our_username()
                medias = self.media_controller.get_recent_media_by_tag(tag=self.current_tag,
                                                                       excluded_owner_usernames=[our_username])

                medias = random.sample(medias, int(len(medias) * self.select_ratio))

                logging.info("[INSTABOT] For tag %s was picked media: %s",
                             self.current_tag, [media.shortcode for media in medias])

                self.schedule_and_execute_actions_for_medias(medias)

            # TODO: Dont sleep on 404, the user probably just deleted the media/changed username
            except instabotpatrik.client.InstagramResponseException as e:
                logging.critical(e, exc_info=True)
                logging.critical("Unsatisfying response from Instagram. Request [%s] %s returned code: %d. "
                                 "Botting might had been detected. Will sleep approximately %d seconds now.",
                                 e.request_type, e.request_address, e.return_code, self.ban_sleep_time_sec)
                instabotpatrik.tools.go_sleep(duration_sec=self.ban_sleep_time_sec, plusminus=120)
            except Exception as e:
                logging.error(e, exc_info=True)
                logging.error("Something went wrong. Will sleep 60 seconds")
                instabotpatrik.tools.go_sleep(duration_sec=60, plusminus=10)

        logging.info("Bot is stopped.")

    def stop(self):
        self._stopped = True
        logging.info("Stopped flag was set.")
