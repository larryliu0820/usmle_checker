# Created by Larry Liu
#
# Date: 5/4/2019
import functools
import getpass
import os
import logging
import random
import time
import argparse

from dotenv import load_dotenv
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException, \
    StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from util import EmailUtil, ERROR_EMAIL_SUBJECT, SUCCESS_EMAIL_SUBJECT, RESERVED_EMAIL_SUBJECT, \
    PhoneCallUtil

logging.basicConfig(filename='checker.log', filemode='w', format='%(asctime)s - %(levelname)s - %(message)s',
                    level=logging.INFO)


class Checker(object):
    URL = "https://csessauthentication.ecfmg.org/"
    HOME_URL = "https://csess2.ecfmg.org/home.aspx"
    USERNAME_ID = "txtUsmleId"
    PASSWORD_ID = "txtPassword"
    LOGIN_BTN_ID = "btnLogin"
    WEB_AUTH_ID = "webauth"
    EMERGENCY_CONT_INFO_ID = "frmEmergencyContInfo"
    SKIP_BTN_ID = "btnSkip"
    HOME_ID = "frmHome"
    CALENDAR_PAGE_ID = "frmCal"
    CONFIRM_PAGE_ID = "pnlConfirm"
    CALENDAR_BTN_TEXT = "View Available Test Dates"
    LOS_ANGELES_BTN_ID = "rdFacilityList_2"
    CHCAGO_BTN_ID = "rdFacilityList_3"
    HOUSTON_BTN_ID = "rdFacilityList_4"
    ATLANTA_BTN_ID = "rdFacilityList_1"
    PHILADELPHIA_BTN_ID = "rdFacilityList_0"
    CITY_BTN_MAP = {"Philadelphia": PHILADELPHIA_BTN_ID, "Atlanta": ATLANTA_BTN_ID, "LA": LOS_ANGELES_BTN_ID,
                    "Chicago": CHCAGO_BTN_ID, "Houston": HOUSTON_BTN_ID}
    BTN_CITY_MAP = {PHILADELPHIA_BTN_ID: "Philadelphia", ATLANTA_BTN_ID: "Atlanta", LOS_ANGELES_BTN_ID: "LA",
                    CHCAGO_BTN_ID: "Chicago", HOUSTON_BTN_ID: "Houston"}
    SPACE_NOT_FOUND_ERR_ID = "lblErrMsg"
    MONTH_SELECT_LIST_ID = "sSelectCal"
    CALENDAR_XPATH = '//*[@bordercolor="#808080" and @bgcolor="#ffffff"]/tbody/tr/td/table'

    def email_exception(func):
        @functools.wraps(func)
        def wrapped(inst, *args, **kwargs):
            try:
                return func(inst, *args, **kwargs)
            except (TimeoutException, NoSuchElementException, ElementClickInterceptedException,
                    StaleElementReferenceException) as e:
                inst.email_util.send_email(ERROR_EMAIL_SUBJECT, "Error:", inst.browser.page_source)
                logging.error("Error occurred!", exc_info=True)
                raise e

        return wrapped

    def __init__(self):
        load_dotenv()
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        dir_path = os.path.dirname(os.path.realpath(__file__))
        self.browser = webdriver.Firefox(executable_path=dir_path + '/geckodriver')
        self.wait = WebDriverWait(self.browser, 30)
        self.email_util = EmailUtil()
        self.call_util = PhoneCallUtil()
        self.username = os.getenv('USMLE_USERNAME') or input("Please type in your USMLE login username: ")
        self.password = os.getenv('USMLE_PASSWORD') or getpass.getpass("Please type in your USMLE login password: ")

    @email_exception
    def start(self):
        self.browser.get(self.URL)
        self.wait.until(EC.presence_of_element_located((By.ID, self.WEB_AUTH_ID)))
        logging.debug('Going to %s' % self.URL)

    @email_exception
    def login(self) -> bool:
        username_elem = self.browser.find_element_by_id(self.USERNAME_ID)
        password_elem = self.browser.find_element_by_id(self.PASSWORD_ID)

        username_elem.send_keys(self.username)
        password_elem.send_keys(self.password)
        logging.info('Filling in:')
        logging.info('Username:    %s' % self.username)
        logging.info('Password:    %s' % ('*' * len(self.password)))

        logging.info('\nLogin Clicked.')
        return self.click_by_id(self.LOGIN_BTN_ID, self.EMERGENCY_CONT_INFO_ID)

    @email_exception
    def go_to_home_page(self):
        self.browser.get(self.HOME_URL)
        self.wait.until(EC.presence_of_element_located((By.ID, self.HOME_ID)))
        return True

    @email_exception
    def click_by_id(self, button_id: str, expect_id: str = None) -> bool:
        return self.click_elem(self.browser.find_element_by_id(button_id), expect_id)

    @email_exception
    def click_by_text(self, button_text: str, expect_id: str = None) -> bool:
        return self.click_elem(self.browser.find_element_by_link_text(button_text), expect_id)

    @email_exception
    def check_city_month(self, city_id: str, month_id: str, day_range: list = None) -> list:
        initial_cal = self.get_calendar_for_city(city_id)
        if initial_cal is None:
            return []
        month_cal = self.get_calendar_for_month(initial_cal, month_id)
        if month_cal is None:
            return []
        available_dates = Checker.get_available_dates_in_month(month_cal)
        if not day_range or not all(day in range(1, 32) for day in day_range):
            day_range = range(1, 32)
        available_dates_in_range = [day for day in available_dates if int(day.text.split('\n')[0]) in day_range]
        if available_dates_in_range:
            self.call_util.call()
            logging.warning(
                "Congrats! We find you available spot! Sending email to %s" % self.email_util.receiver_email)
            self.email_util.send_email(self.BTN_CITY_MAP[city_id], "",
                                       month_cal.get_attribute('innerHTML'))
            return available_dates_in_range
        else:
            return []

    @email_exception
    def reserve_if_available(self, city_name: str, month_id: str, day_range: list = None):
        logging.info('Checking %s %s' % (city_name, month_id))
        city_id = self.CITY_BTN_MAP[city_name]
        days = self.check_city_month(city_id, month_id, day_range)
        if days:
            logging.warning(
                "Congrats! Reservation is successful! Sending email to %s" % self.email_util.receiver_email)
            self.reserve(days[0])
            self.start_a_new_browser_to_reserve(city_id, month_id, day_range)
        else:
            wait_sec = random.randint(1, 2)
            logging.info('Wait for %d seconds' % wait_sec)
            time.sleep(wait_sec)

    @email_exception
    def reserve(self, day: WebElement) -> bool:
        logging.info('Clicking on %s' % day.text.split('\n')[0])
        return self.click_elem(day.find_element_by_tag_name('a'), self.CONFIRM_PAGE_ID)

    @email_exception
    def get_calendar_for_city(self, city_id: str, force_refresh: bool = True) -> WebElement:
        city_option = self.browser.find_element_by_id(city_id)
        if not city_option.get_attribute('checked'):
            logging.info('Click on %s' % city_id)
            self.click_by_id(city_id)
            logging.info('Get calendar')
            return self.get_calendar()
        else:
            if self.has_no_space_err_msg():
                if force_refresh:
                    self.click_by_id(self.get_city_id_different_from(city_id))
                    return self.get_calendar_for_city(city_id, False)
                else:
                    return None
            else:
                logging.info('Get calendar')
                return self.get_calendar()

    @email_exception
    def has_no_space_err_msg(self) -> bool:
        try:
            msg = self.browser.find_element_by_id(self.SPACE_NOT_FOUND_ERR_ID)
            return msg is not None
        except NoSuchElementException:
            return False

    @email_exception
    def get_city_id_different_from(self, city_id: str) -> str:
        for value in self.CITY_BTN_MAP.values():
            if value is not city_id:
                return value

    @email_exception
    def get_calendar_for_month(self, cal: WebElement, month_id: str) -> WebElement:
        month_select_list = cal.find_element_by_id(self.MONTH_SELECT_LIST_ID)
        month_option = month_select_list.find_element_by_xpath(
            '//select[@id="%s"]/option[@value="%s"]' % (self.MONTH_SELECT_LIST_ID, month_id))
        return self.get_calendar(refresh_button=month_option)

    @email_exception
    def click_elem(self, button: WebElement, expect_id: str = None) -> bool:
        self.browser.execute_script("window.scrollTo(0, %s)" % button.location['y'])
        button.click()
        if expect_id:
            self.wait.until(EC.presence_of_element_located((By.ID, expect_id)))
        return True

    @email_exception
    def get_calendar(self, refresh_button: WebElement = None) -> WebElement:
        try:
            old_calendar = self.browser.find_element_by_xpath(self.CALENDAR_XPATH)
            if refresh_button:
                self.click_elem(refresh_button)
                self.wait.until(EC.staleness_of(old_calendar))
                return self.browser.find_element_by_xpath(self.CALENDAR_XPATH)
            else:
                return old_calendar
        except NoSuchElementException:
            try:
                self.browser.find_element_by_id(self.SPACE_NOT_FOUND_ERR_ID)
                return None
            except NoSuchElementException:
                pass
            self.wait.until(EC.presence_of_element_located((By.XPATH, self.CALENDAR_XPATH)))
            return self.browser.find_element_by_xpath(self.CALENDAR_XPATH)

    @email_exception
    def start_a_new_browser_to_reserve(self, city_id: str, month_id: str, day_range: list = None):
        self.browser.save_screenshot('./success.png')
        dir_path = os.path.dirname(os.path.realpath(__file__))
        self.browser = webdriver.Firefox(executable_path=dir_path + '/geckodriver')
        self.wait = WebDriverWait(self.browser, 30)
        self.start()
        self.login()
        self.click_by_id(self.SKIP_BTN_ID, self.HOME_ID)
        self.click_by_text(self.CALENDAR_BTN_TEXT, self.CALENDAR_PAGE_ID)
        days = self.check_city_month(city_id, month_id, day_range)
        if days:
            success = self.reserve(days[0])
            if success:
                exit(0)

    @staticmethod
    def get_available_dates_in_month(month: WebElement) -> list:
        week_list = month.find_elements_by_tag_name("tr")[3:9]
        return [item for week in week_list for item in Checker.get_available_dates_in_week(week)]

    @staticmethod
    def get_available_dates_in_week(week_cal: WebElement) -> list:
        day_list = week_cal.find_elements_by_tag_name("td")
        return [day for day in day_list if Checker.is_day_available(day)]

    @staticmethod
    def is_day_available(day: WebElement) -> bool:
        class_val = day.get_attribute("class")
        return class_val and (len(class_val) is not 0) and ('NON' not in class_val)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Specify the city to be monitored, after "--city". For example '
                                                 '"--city LA" or "--city Houston".')
    parser.add_argument('--city', nargs='*', type=str, default=['LA'], help='The name of the city. Supports "LA" '
                                                                            ', "Houston", "Chicago", "Philadelphia"')
    args = parser.parse_args()
    cities = args.city
    my_checker = Checker()
    while True:
        my_checker.start()
        my_checker.login()
        logging.info('Going to home page')
        my_checker.click_by_id(my_checker.SKIP_BTN_ID, my_checker.HOME_ID)

        logging.info('Clicking on calendar button')
        my_checker.click_by_text(my_checker.CALENDAR_BTN_TEXT, my_checker.CALENDAR_PAGE_ID)
        while True:
            try:
                for city in cities:
                    my_checker.reserve_if_available(city, "6-2019", list(range(15, 32)))
                    my_checker.reserve_if_available(city, "7-2019", list(range(1, 5)))
            except (TimeoutException, NoSuchElementException, ElementClickInterceptedException,
                    StaleElementReferenceException) as e:
                my_checker.email_util.send_email(ERROR_EMAIL_SUBJECT, "Error:", my_checker.browser.page_source)
                logging.error('Error occurred!', exc_info=True)
                logging.warning('Retry login')
                break
