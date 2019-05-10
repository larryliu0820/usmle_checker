# Created by Larry Liu
#
# Date: 5/4/2019
# !/usr/bin/env python
import functools

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from util import EmailUtil, ERROR_EMAIL_SUBJECT, SUCCESS_EMAIL_SUBJECT


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
    CALENDAR_BTN_TEXT = "View Available Test Dates"
    LOS_ANGELES_BTN_ID = "rdFacilityList_2"
    MONTH_SELECT_LIST_ID = "sSelectCal"
    CALENDAR_XPATH = '//*[@id="lblUserHeading"]/table/tbody/tr[9]/td/table/tbody/tr[1]/td/table[2]/tbody/tr/td[' \
                     '4]/table/tbody/tr[3]/td[1]/table[1]/tbody/tr/td/table'

    def email_exception(func):
        @functools.wraps(func)
        def wrapped(inst, *args, **kwargs):
            try:
                return func(inst, *args, **kwargs)
            except (TimeoutException, NoSuchElementException, ElementClickInterceptedException) as e:
                inst.email_util.send_email(ERROR_EMAIL_SUBJECT, "Error:", inst.browser.page_source)
                with open('./debug.html', mode='w', encoding='utf-8') as f:
                    f.write(inst.browser.page_source)
                raise e

        return wrapped

    def __init__(self):
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--disable-gpu')
        self.browser = webdriver.Chrome(executable_path='./chromedriver', chrome_options=chrome_options)
        self.wait = WebDriverWait(self.browser, 10)
        self.email_util = EmailUtil()
        try:
            self.browser.get(self.URL)
            self.wait.until(EC.presence_of_element_located((By.ID, self.WEB_AUTH_ID)))
            print('Going to %s' % self.URL)
        except TimeoutException as e:
            self.email_util.send_email(ERROR_EMAIL_SUBJECT, str(e))

    @email_exception
    def login(self, username: str = None, password: str = None) -> bool:
        username_elem = self.browser.find_element_by_id(self.USERNAME_ID)
        password_elem = self.browser.find_element_by_id(self.PASSWORD_ID)

        username_elem.send_keys(username)
        password_elem.send_keys(password)
        print('Filling in:')
        print('Username:    %s' % username)
        print('Password:    %s' % ('*' * len(password)))

        print('\nLogin Clicked.')
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
    def check_city_month(self, city_id: str, month_id: str):
        initial_cal = self.get_calendar_for_city(city_id)
        month_cal = self.get_calendar_for_month(initial_cal, month_id)
        available_dates = Checker.get_available_dates_in_month(month_cal)
        if available_dates:
            print("Congrats! We find you available spot! Sending email to %s" % self.email_util.receiver_email)
            self.email_util.send_email(SUCCESS_EMAIL_SUBJECT, "See below: \n",
                                       month_cal.get_attribute('innerHTML'))

    @email_exception
    def get_calendar_for_city(self, city_id: str) -> WebElement:
        self.click_by_id(city_id)
        print('Get calendar')
        return self.get_calendar()

    @email_exception
    def get_calendar_for_month(self, cal: WebElement, month_id: str) -> WebElement:
        month_select_list = cal.find_element_by_id(self.MONTH_SELECT_LIST_ID)
        month_option = month_select_list.find_element_by_xpath(
            '//select[@id="%s"]/option[@value="%s"]' % (self.MONTH_SELECT_LIST_ID, month_id))
        month_option.click()
        self.wait.until(EC.presence_of_element_located((By.ID, self.CALENDAR_PAGE_ID)))
        return self.get_calendar()

    @email_exception
    def click_elem(self, button: WebElement, expect_id: str = None) -> bool:
        self.browser.execute_script("window.scrollTo(0, %s)" % button.location['y'])
        button.click()
        if expect_id:
            self.wait.until(EC.presence_of_element_located((By.ID, expect_id)))
        return True

    @email_exception
    def get_calendar(self) -> WebElement:
        return self.browser.find_element_by_xpath(self.CALENDAR_XPATH)

    @staticmethod
    @email_exception
    def get_available_dates_in_month(month: WebElement) -> list:
        week_list = month.find_elements_by_tag_name("tr")[3:9]
        return [item for week in week_list for item in Checker.get_available_dates_in_week(week)]

    @staticmethod
    @email_exception
    def get_available_dates_in_week(week_cal: WebElement) -> list:
        day_list = week_cal.find_elements_by_tag_name("td")
        week_cal.get_attribute("class")
        return [(day.text, day.get_attribute("class")) for day in day_list if Checker.is_day_available(day)]

    @staticmethod
    def is_day_available(day: WebElement) -> bool:
        class_val = day.get_attribute("class")
        return class_val and (len(class_val) is not 0) and ('NON' not in class_val)


if __name__ == "__main__":
    my_checker = Checker()
    my_checker.login()

    print('Going to home page')
    my_checker.click_by_id(my_checker.SKIP_BTN_ID, my_checker.HOME_ID)

    print('Clicking on calendar button')
    my_checker.click_by_text(my_checker.CALENDAR_BTN_TEXT, my_checker.CALENDAR_PAGE_ID)

    while True:
        print('Checking Los Angeles June 2019')
        my_checker.check_city_month(my_checker.LOS_ANGELES_BTN_ID, "06-2019")
