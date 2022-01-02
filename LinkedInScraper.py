from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait

import time
from typing import List, Set

from Employee import Employee
from Experience import Experience
from Education import Education
from LinkedInDBAccess import LinkedInDB


def ReadEmployeeURLsFromFile(textFilePath):
    ans = []
    with open(textFilePath, "r") as file:
        for i, line in enumerate(file):
            ans.append(line)

    return ans

def WriteEmployeeURLsToFile(textFilePath, empURLs):
    with open(textFilePath, "w") as file:
        for URL in empURLs:
            file.write(URL + '\n')

def GetUsernameAndPassword(textFilePath):
    with open(textFilePath, "r") as file:
        username = ""
        password = ""
        for i, line in enumerate(file):
            if i == 0:
                username = line
            elif i == 1:
                password = line

        return username, password

"""
LinkedInScraper

Description:
    Utilizes selenium and chrome driver to authentication the user session for LinkedIn access.
    Provides methods to extract relevant data from LinkedIn
"""

class LinkedInScraper:
    # Dev Note: 11/16/2021 WORKING
    # Initializes driver
    def __init__(self, username, password, driver_path, database: LinkedInDB):
        # Database connection and methods for inserting employee information
        self.database = database

        # Stores the URL of each employee discovered in a LinkedIn query
        if self.database is None:
            self.employeeURLs = []
        else:
            self.employeeURLs = self.database.__LoadEmployeeURLs__()

        if len(self.employeeURLs) == 0:
            self.employeeURLs = ReadEmployeeURLsFromFile("employeeURLs.txt")

        # Specifying options to help driver be more efficient
        chrome_options = webdriver.ChromeOptions()

        chrome_options.headless = True
        chrome_options.add_argument("--window-size=1920x1080")

        self.driver = webdriver.Chrome(executable_path=driver_path, options=chrome_options)

        self.driver.get("https://linkedin.com/home")

        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR,
                     "#session_key"))).send_keys(username)

            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR,
                     "#session_password"))).send_keys(password)

            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(
                    (By.XPATH,
                     "/html/body/main/section[1]/div/div/form/button"))).click()
        except TimeoutException:
            print("ERROR: Could not login properly")
            self.driver = None
            return

        # Sometimes I am stopped for being a robot, this gives me time to prove I'm human
        # Otherwise, proceeds with program execution if element is found
        try:
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR,
                     "#voyager-feed")))
        except TimeoutException:
            print("ERROR: Captcha needed")

    """
    LinkedInScraper::AddEmployeeURLsFromSearchPage

    Description:
        Adds all unique employee URLs to the employeeURLs set
    """
    def AddEmployeeURLsFromSearchPage(self):
        main = None
        tries = 0

        self.driver.execute_script("window.scrollTo(0, 2000)")

        while main is None and tries < 5:
            try:
                tries += 1
                main = self.driver.find_element(By.TAG_NAME, "main")
                print("Success")
            except NoSuchElementException:
                print(f"Couldn't find element, retrying... {5 - tries} more times")

        if main is None:
            return

        peopleDiv = main.find_element(By.XPATH, "./div/div/div[2]")
        peopleList = peopleDiv.find_elements(By.TAG_NAME, "li")
        for i, element in enumerate(peopleList):
            # Can be no more than 10 results per page
            # Need to have better break criteria than this
            if i > 9:
                break
            XPathLocation = f"./div/div/div[2]/div[1]/div[1]/div/span[1]/span/a[@href]"
            try:
                link = element.find_element(By.XPATH, XPathLocation).get_attribute("href")
                print(link)

                # Checks if profile is accessible (Not "LinkedIn Member")
                if link[25:27] == "in":
                    # Format link to only include profile ID
                    endLinkPosition = 0
                    for i, char in enumerate(link):
                        if char == '?':
                            endLinkPosition = i

                    URL = link[:endLinkPosition]
                    if URL not in self.employeeURLs:
                        self.employeeURLs.append(URL)
                # Otherwise, the link has no relevance
            except NoSuchElementException:
                print(f"Inspect element at {XPathLocation}")

            print("*****************************************")

    """
    LinkedInScraper::LinkedInPeopleSearch

    Description:
        After authentication, converts the query into a format recognizable to LinkedIn 
        and passes the query into LinkedIn's search engine and calls the
        AddEmployeeURLsFromSearchPage to append to employeeURLs set

    Parameters:
        query - A string entered in how you would in the LinkedIn GUI. Converted into a URL query argument
    """

    def LinkedInPeopleSearch(self, query: str):
        oldLen = len(self.employeeURLs)
        # Convert query string to a URLQuery
        queryArr = query.split(' ')
        URLQuery = ''

        for i, searchTerm in enumerate(queryArr):
            searchTerm = searchTerm.replace('&', '%26')
            if i == 0:
                URLQuery = searchTerm
            else:
                # LinkedIn Separates Search Terms by %20 instead of whitespace
                URLQuery += ('%20' + searchTerm)

        # Navigate to webpage
        self.driver.get(f"https://www.linkedin.com/search/results/people/?keywords={URLQuery}")

        # JS Elements were not rendering without scrolling
        self.driver.execute_script("window.scrollTo(0, 2000)")

        pageButtonCount = None

        main = None
        try:
            main = self.driver.find_element(By.TAG_NAME, "main")
        except NoSuchElementException:
            print("Could not find main")
            return

        try:
            div1 = main.find_element(By.TAG_NAME, "div")
            div2 = div1.find_element(By.TAG_NAME, "div")
            div3 = div2.find_elements(By.TAG_NAME, "div")
            div4 = div3[4].find_element(By.TAG_NAME, "div")
            div5 = div4.find_element(By.TAG_NAME, "div")
            ul = div5.find_element(By.TAG_NAME, "ul")
            list = ul.find_elements(By.TAG_NAME, "li")
            span = list[-1].find_elements(By.TAG_NAME, "span")
            pageButtonCount = span
        except NoSuchElementException:
            print("Element not found, trying new location")

        if pageButtonCount is None:
            try:
                pageButtonCount = main.find_element(By.XPATH,
                    "./div/div/div[5]/div/div/ul/li[last()]/button/span")
            except NoSuchElementException:
                print("Element not found, trying new location")

        if pageButtonCount is None:
            # For whatever reason, sometimes the element is located at this xpath
            try:
                pageButtonCount = main.find_element(By.XPATH,
                    "./div/div/div[4]/div/div/ul/li[last()]/button/span")
            except NoSuchElementException:
                print("Element not found, trying new location")

        if pageButtonCount is None:
            try:
                pageButtonCount = self.driver.find_element( By.XPATH,
                    "/html/body/div[5]/div[3]/div/div[2]/div/div[1]/main/div/div/div[5]/div/div/ul/li[10]/button/span")
            except NoSuchElementException:
                print("Element not found, defaulting to 0")

        if pageButtonCount is not None:
            maxPageCount = int(pageButtonCount.text)
        else:
            maxPageCount = 0

        for page in range(maxPageCount):
            print("Parsing Page", page)
            if page != 1:
                self.driver.get(f"https://www.linkedin.com/search/results/people/?keywords={URLQuery}&page={str(page)}")
            self.AddEmployeeURLsFromSearchPage()

        print("Done with extracting URLs from Search...")
        newLen = len(self.employeeURLs)
        additions = newLen - oldLen
        print("New Entries:", additions)

    def ExtractEmployeeExperiences(self, employeeURL):
        experiences = []
        # profileurl/details/experience
        self.driver.get(employeeURL+"/details/experience")
        # All information contained within <main>
        expSection = None
        try:
            expSection = self.driver.find_element_by_tag_name("main")

        except NoSuchElementException:
            return []
        # From main: div[2]/div/div/ul

        '''
        # If experience can be expanded, click the button
        try:
            # Expand experiences
            expButtons = expSection.find_elements_by_tag_name("button")

            for expButton in expButtons:
                expButton.click()
        except NoSuchElementException:
            pass
        '''

        # Extracting Top-level <li> tags from Experience Section
        expList = None

        ul = None
        try:
            ul = WebDriverWait(expSection, 2).until(
                EC.presence_of_element_located(
                    (By.XPATH,
                     "./section/div[2]/div/div[1]/ul")))

            # print()
            # print("==================== UL ====================")
            # print(ul.text)
            # print()

            try:
                # Assuming the workers can have no more than 100 jobs
                expList = ul.find_elements_by_xpath("./li")
            except NoSuchElementException:
                pass

        except TimeoutException:
            print("ERROR: Could not find experience list (1)")
            return [-1]

        for i, exp in enumerate(expList):
            # print()
            # print("==================== NEW EXP ====================")
            # print(expList[i].text)
            # print()

            # Check for type
            expSublist = None
            try:
                # This can trigger for elements with descriptions
                # (Single elements store their descriptions at the same location)
                ul = WebDriverWait(expList[i], 2).until(
                    EC.presence_of_element_located(
                        (By.TAG_NAME,
                         "ul")))
                ul2 = WebDriverWait(ul, 2).until(
                    EC.presence_of_element_located(
                        (By.TAG_NAME,
                         "ul")))

                try:
                    # Test to see if subList
                    pointForSubExp = exp.find_element_by_xpath("./div/div[2]/div[2]/ul/li/div/div/div[1]/ul/li[1]/span")
                    expSublist = ul2.find_elements_by_xpath("./li")
                except NoSuchElementException:
                    pass
            except TimeoutException:
                pass

            # List of Elements
            if expSublist:
                company = ""
                try:
                    company = exp.find_element_by_xpath("./div/div[2]/div[1]/a/div/span/span[1]").text
                except NoSuchElementException:
                    print("ERROR: Could not find company [1]")
                    return [-1]

                jobType = ""
                # If this field is found, it applies to all subExp elements
                try:
                    # Comes in the format <Full-time · 7 mos>
                    jobType = exp.find_element_by_xpath("./div/div[2]/div[1]/a/span[1]/span[1]").text.split()[0]
                except NoSuchElementException:
                    pass

                location = ""
                try:
                    location = exp.find_element_by_xpath("./div/div[2]/div[1]/a/span[2]/span[1]").text
                except NoSuchElementException:
                    pass

                for subExp in expSublist:
                    experience = Experience()

                    experience.company_name = company
                    # Position
                    try:
                        experience.position = subExp.find_element_by_xpath(
                            "./div/div[2]/div/a/div/span/span[1]").text

                    except NoSuchElementException:
                        print("ERROR: Could not find position [1]")
                        return [-1]

                    # Type (Optional)
                    if jobType != "":
                        experience.employment_type = jobType
                    else:
                        try:
                            experience.employment_type = subExp.find_element_by_xpath(
                                "./div/div/div[1]/ul/li[1]/div/div[2]/div/a/span[1]").text
                        except NoSuchElementException:
                            pass

                    if location != "":
                        experience.location = location
                    else:
                        # Location (Optional)
                        try:
                            experience.location = subExp.find_element_by_xpath(
                                "./div/div[2]/div/a/span[3]/span[1]").text
                        except NoSuchElementException:
                            pass

                    # Dates
                    try:
                        dates = subExp.find_element_by_xpath(
                            "./div/div[2]/div/a/span/span[1]").text
                        # Nov 2021 - Present · 2 mos
                        dashInd = dates.rindex("-")
                        experience.start_date = dates[:dashInd].strip()
                        try:
                            dotInd = dates.rindex('·')
                            experience.end_date = dates[dashInd + 2:dotInd].strip()
                        except ValueError:
                            experience.end_date = dates[dashInd + 2:].strip()
                    except NoSuchElementException:
                        pass

                    experience.description = None
                    experience.media = None

                    print(experience)
                    experiences.append(experience)

            # Single Element
            else:
                experience = Experience()

                # Position
                try:
                    experience.position = exp.find_element_by_xpath("./div/div[2]/div/div[1]/div/span/span[1]").text
                except NoSuchElementException:
                    print("ERROR: Could not find position [2]")
                    return [-1]

                # Company and Type
                try:
                    companyAndType = exp.find_element_by_xpath("./div/div[2]/div/div[1]/span[1]/span[1]").text

                    try:
                        dotInd = companyAndType.rindex('·')
                        experience.company_name = companyAndType[:dotInd].strip()
                        experience.employment_type = companyAndType[dotInd + 1:].strip()
                    except ValueError:
                        experience.company_name = companyAndType

                except NoSuchElementException:
                    print("ERROR: Could not find company [3]")
                    return [-1]

                # Location (Optional)
                try:
                    experience.location = exp.find_element_by_xpath("./div/div[2]/div/div[1]/span[3]/span[1]").text
                except NoSuchElementException:
                    pass

                # Dates
                try:
                    dates = exp.find_element_by_xpath("./div/div[2]/div/div[1]/span[2]/span[1]").text
                    # Nov 2021 - Present · 2 mos
                    dashInd = dates.rindex("-")
                    experience.start_date = dates[:dashInd].strip()
                    try:
                        dotInd = dates.rindex('·')
                        experience.end_date = dates[dashInd + 2:dotInd].strip()
                    except ValueError:
                        experience.end_date = dates[dashInd + 2:].strip()
                except NoSuchElementException:
                    pass

                # Description (Optional)
                try:
                    experience.description = exp.find_element_by_xpath("./div/div[2]/div[2]/ul/li/div/ul/li/div/div/div/span[1]").text
                except NoSuchElementException:
                    pass

                experience.media = None

                print(experience)
                print()
                experiences.append(experience)

        return experiences

    def ExtractEmployeeEducation(self, employeeURL):
        print("Extracting education from:", employeeURL)
        education = []
        self.driver.get(employeeURL + "/details/education")

        main = None
        try:
            main = WebDriverWait(self.driver, 2).until(
                EC.presence_of_element_located(
                    (By.TAG_NAME,
                     "main")))
        except TimeoutException:
            print("Could not find main")
            return []

        educationList = None
        try:
            ul = main.find_element(By.TAG_NAME, "ul")
            educationList = ul.find_elements(By.XPATH, "./child::*")
        except NoSuchElementException:
            print("Could not find education list")
            educationList = []

        for educationElem in educationList:
            edu = Education()
            try:
                degreeLine = educationElem.find_element(By.XPATH, "./div/div[2]/div[1]/a/span[1]/span[1]").text
                degreeArr = degreeLine.split(", ")
                edu.degree = degreeArr[0]
                edu.degree_type = degreeArr[-1]
            except:
                print("Could not find degree information")
                return []

            try:
                edu.institution = educationElem.find_element(By.XPATH, "./div/div[2]/div[1]/a/div/span/span[1]").text
            except NoSuchElementException:
                pass

            descList = None
            try:
                ul = educationElem.find_element(By.TAG_NAME, "ul")
                descList = ul.find_elements(By.XPATH, "./child::*")
            except NoSuchElementException:
                print("Could not find description list")
                descList = []

            for elem in descList:
                string = elem.text
                grade = "Grade:"
                pos = string.find(grade)
                if pos != -1:
                    # For eliminating duplicates (some fields are stored twice in the HTML, sometimes hidden)
                    start = pos + 1 + len(grade)
                    pos2 = string[start:].find(grade)
                    if pos2 != 1:
                        edu.GPA = string[start:start + pos2].strip()
                    else:
                        edu.GPA = string[start:].strip()
                    continue

                activities = "Activities and societies:"
                pos = string.find(activities)
                if pos != -1:
                    start = pos + 1 + len(activities)
                    pos2 = string[start:].find(activities)
                    if pos2 != -1:
                        edu.activities = string[start: start + pos2].strip()
                    else:
                        edu.activities = string[start:].strip()
                    continue

                # May require additional logic if repeated
                try:
                    edu.description = elem.find_element(By.XPATH, "./div/ul/li/div/div/div/span[1]").text
                except NoSuchElementException:
                    print("Could not extract description")
                    edu.description = ""

            edu.media = None

            dates = educationElem.find_element(By.XPATH, "./div/div[2]/div[1]/a/span[2]/span[1]").text
            dateArr = dates.split(" - ")
            edu.start_date = dateArr[0]
            edu.end_date = dateArr[-1]

            education.append(edu)

        return education

    def ExtractEmployeeSkills(self, employeeURL):
        print("Extracting skills from:", employeeURL)
        skills = {}
        # Navigate to skills webpage
        self.driver.get(employeeURL + "/details/skills")

        notFound = True
        tries = 0
        while notFound or tries < 5:
            try:
                skillTitle = self.driver.find_element(
                    By.XPATH, "/html/body/div[6]/div[3]/div/div/div[2]/div/div/main/section/div[1]/div/h2").text
                if skillTitle == "Skills":
                    notFound = False
            except NoSuchElementException:
                pass

            tries += 1

        if notFound:
            print("Skills page didn't load properly")
            return {}

        main = None
        try:
            main = WebDriverWait(self.driver, 2).until(
                EC.visibility_of_element_located(
                    (By.TAG_NAME,
                     "main")))
        except TimeoutException:
            print("Could not find main")
            return {}

        buttonParent = None
        try:
            buttonParent = WebDriverWait(main, 2).until(
                EC.presence_of_element_located(
                    (By.XPATH,
                     "./section/div[2]/div[1]")))
        except TimeoutException:
            print("Could not find buttons [1]")
            return {}

        buttons = None
        try:

            buttons = buttonParent.find_elements(By.TAG_NAME, "button")
        except NoSuchElementException:
            print("Could not find buttons [2]")
            return {}

        # Iterate through skills categories (skip first "All" button if more than one button)
        if len(buttons) > 1:
            buttons = buttons[1:]

        for i, button in enumerate(buttons):
            skillCategory = button.text
            skills[skillCategory] = []
            # Click the button
            button.click()
            categoryList = None
            try:
                categoryListParent = main.find_element(By.XPATH, f"./section/div[2]/div[{3 + i}]/div/div/div[1]/ul")
                categoryList = categoryListParent.find_elements(By.XPATH, "./child::*")
            except NoSuchElementException:
                print("Could not extract skill category list")

            # Iterate through individual skills within category
            for skillElem in categoryList:
                skill = skillElem.find_element(By.XPATH, "./div/div[2]/div[1]/a/div/span[1]/span[1]").text
                skills[skillCategory].append(skill)

        return skills


    def ExtractEmployeeAccomplishments(self, employeeURL):
        pass

    # Dev Note: 12/29/2021 WORKING
    def ExtractProfileAttributes(self, employeeURL: str) -> Employee:
        # Navigate to web page
        self.driver.get(employeeURL)

        print("Extracting attributes from: ", employeeURL, sep="")

        # Contains all relevant profile attributes
        main = None
        try:
            main = WebDriverWait(self.driver, 2).until(
                EC.presence_of_element_located(
                    (By.TAG_NAME,
                     "main")))
        except TimeoutException:
            print("ERROR: Could not find <main>")

        # If main cannot be found, no profile elements can be extracted
        if main is None:
            return None

        # Initialize Employee Object
        currentEmployee = Employee()

        # Last split in employeeURL
        currentEmployee.user_url_id = employeeURL.split("/")[-1]

        try:
            nameElement = WebDriverWait(main, 2).until(
                EC.presence_of_element_located(
                    (By.XPATH, "./section[1]/div[2]/div[2]/div[1]/div[1]/h1")))

            if nameElement:
                currentEmployee.name = nameElement.text
        except TimeoutException:
            print("Could not find name")
            return None

        try:
            currentEmployee.location = main.find_element(By.XPATH, "./section[1]/div[2]/div[2]/div[2]/span[1]").text
        except NoSuchElementException:
            pass

        # Header
        try:
            currentEmployee.header = WebDriverWait(main, 2).until(
                EC.presence_of_element_located(
                    (By.XPATH,
                     "./section[1]/div[2]/div[2]/div[1]/div[2]"))).text
        except TimeoutException:
            pass

        try:
            currentEmployee.about = WebDriverWait(main, 2).until(
                EC.presence_of_element_located(
                    (By.XPATH,
                     "./div/div/div[5]/section/div"))).text

            if currentEmployee.about[-8: 0] == "see more":
                currentEmployee.about = currentEmployee.about[:-10]
        except TimeoutException:
            pass

        #currentEmployee.website = None
        currentEmployee.experience = self.ExtractEmployeeExperiences(employeeURL)  # List
        currentEmployee.education = self.ExtractEmployeeEducation(employeeURL)  # List
        currentEmployee.skills = self.ExtractEmployeeSkills(employeeURL)  # Dict
        
        # Deprecated, accomplishments have been reworked
        #currentEmployee.accomplishments = self.ExtractEmployeeAccomplishments(main)  # List

        return currentEmployee

    def BatchLinkedInPeopleSearch(self, queries):
        for query in queries:
            self.LinkedInPeopleSearch(query)

testEmployee = Employee()

testEmployee.user_url_id = "https://www.linkedin.com/in/jacobazevedojr/"
testEmployee.name = "Jacob Azevedo Jr."
testEmployee.location = "San Francisco Bay Area"
testEmployee.header = "This is a test header for Jacob Azevedo"
testEmployee.about = "This is a test about for Jacob Azevedo"
testEmployee.website = None

testEmployee.experience = []
testEmployee.experience.append(Experience())
testEmployee.experience[0].position = "Software Engineer"
testEmployee.experience[0].company_name = "Microsoft"
testEmployee.experience[0].employment_type = "Full-Time"
testEmployee.experience[0].location = "Seattle, WA"
testEmployee.experience[0].description = "This is a job description"
testEmployee.experience[0].media = None
testEmployee.experience[0].start_date = "May 2021"
testEmployee.experience[0].end_date = "Aug 2021"

testEmployee.education = []
testEmployee.education.append(Education())
testEmployee.education[0].degree = "Computer Science"
testEmployee.education[0].degree_type = "Bachelor of Science"
testEmployee.education[0].institution = "California State University, Long Beach"
testEmployee.education[0].GPA = "3.92"
testEmployee.education[0].activities = ""
testEmployee.education[0].description = ""
testEmployee.education[0].media = None
testEmployee.education[0].start_date = "2020"
testEmployee.education[0].end_date = "2022"

testEmployee.skills = {"Main": ["C++", "Python (Programming Language)", "Java"]}
testEmployee.accomplishments = None
