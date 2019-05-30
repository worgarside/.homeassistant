# from selenium import webdriver
#
# # prepare the option for the chrome driver
# options = webdriver.ChromeOptions()
# options.add_argument('headless')
#
# # start chrome browser
# browser = webdriver.Chrome(chrome_options=options)
# browser.get('http://www.google.com/xhtml')
# print(browser.current_url)
# print(browser.page_source)
# browser.quit()


from pyvirtualdisplay import Display
from selenium import webdriver
from time import time

display = Display(visible=0)
display.start()

# now Firefox will run in a virtual display.
# you will not see the browser.
time1 = time()

print(f'1. Display started @ {time1}')
browser = webdriver.Firefox('/usr/local/bin')
time2 = time()
print(f'2. {browser} {time2 - time1}')
browser.get('google.com')
print(browser.title)
browser.quit()

display.stop()





# from selenium import webdriver
#
# driver = webdriver.PhantomJS("C:\\Users\Will Garside\AppData\Roaming\\npm\\node_modules\phantomjs-prebuilt\lib\phantom\\bin\phantomjs.exe")
# driver.set_window_size(1024, 768)
# driver.get(url)
# driver.save_screenshot('./screen.png')
# sleep(3)
# driver.save_screenshot('./screen2.png')