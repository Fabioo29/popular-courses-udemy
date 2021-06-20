import requests
import json
import os

from bs4 import BeautifulSoup
from tqdm import tqdm
from cloudscraper import create_scraper
from argparse import ArgumentParser
from getpass import getpass

LOGIN_URL = "https://www.udemy.com/join/login-popup/?locale=en_US"
REQUEST_URL = "https://www.udemy.com/api-2.0/users/me/subscribed-courses/?ordering=-last_accessed&fields[course]=@min,num_subscribers"

# headers from the browser I've tested
HEADERS = {
        "origin": "https://www.udemy.com",
        "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.106 Safari/537.36",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "content-type": "application/json;charset=UTF-8",
        "x-requested-with": "XMLHttpRequest",
        "x-checkout-version": "2",
        "referer": "https://www.udemy.com/",
}

def clearConsole():
    """
    Clear the command prompt console according to user OS
    
    """

    command = 'clear'
    if os.name in ('nt', 'dos'): 
        command = 'cls'
    os.system(command)

def main(*args):
    """
    Loads user inputs and uses Udemy api (https://www.udemy.com/developers/affiliate/)
    
    Print out the most popular courses on user's account
    """

    # request session and scraper
    session = requests.Session()    
    scraper = create_scraper()

    # verify if there's a saved cookie file
    if not os.path.isfile("cookie.cookie"):

        # find csrf form token
        response = scraper.get(LOGIN_URL)
        soup = BeautifulSoup(response.content, "html.parser")
        csrf_token = soup.find("input", {"name": "csrfmiddlewaretoken"})["value"]

        
        # create dict with form data    
        form_data = {
            'csrfmiddlewaretoken': csrf_token,
            'email': input('Udemy login email: '),
            'password': getpass('Udemy login password: ')
        }

        # clear console
        clearConsole()

        # add needed data to scraper headers and login(POST) with form data
        scraper.headers.update({"Referer": LOGIN_URL})
        auth_response = scraper.post(LOGIN_URL, data=form_data, allow_redirects=False)

        # get needed info from browser cookies after login successful    
        if auth_response.status_code != 302:
            raise Exception(
                f"Could not login. Code: {auth_response.status_code} Text: {auth_response.text}"
            )
        else:
            cookie_details = {
                "csrf_token": csrf_token,
                "access_token": auth_response.cookies["access_token"],
                "client_id": auth_response.cookies["client_id"],
            }

        # update headers with data to authorize udemy api access
        bearer_token = f"Bearer {cookie_details['access_token']}"
        session.headers = HEADERS
        session.headers.update(
            {
                "authorization": bearer_token,
                "x-udemy-authorization": bearer_token,
            }
        )

        # save cookies for api request
        with open("cookie.cookie", "a+") as f:
            f.write(json.dumps(session.headers))

    else:
        with open("cookie.cookie") as f:
            session.headers = json.loads(f.read())

    # get most popular courses from udemy api (json)
    Saved_courses = {'students':[], 'title': [], 'url': []}
    page_size = 100

    if args[0].keywords != ' ':
        keywords = ("+".join(args[0].keywords.replace(',', '').split(' ')))
    else:
        keywords = args[0].keywords

    total_pages = json.loads(session.get(REQUEST_URL + f"&page={1}&page_size={100}&search={keywords}").text)["count"] // page_size
    
    for i in tqdm(range(args[0].top), desc="loading courses"):
        max_temp = {'students': -1, 'title': '', 'url': ''}

        for page in range(1, total_pages + 2):
            data = json.loads(session.get(REQUEST_URL + f"&page={page}&page_size={100}&search={keywords}").text)
            
            for course in data['results']:
                if course['num_subscribers'] > max_temp['students'] and course['title'] not in  Saved_courses['title']:
                    max_temp['students'], max_temp['title'], max_temp['url'] = course['num_subscribers'], course['title'], course['url']
        
        if max_temp['students'] > -1:
            Saved_courses['students'].append(max_temp['students'])
            Saved_courses['title'].append(max_temp['title'])
            Saved_courses['url'].append('https://www.udemy.com' + max_temp['url'])
    
    for i in range(len(Saved_courses['students'])):
        print(f"\nStudents: {Saved_courses['students'][i]}\n{Saved_courses['title'][i]}\n{Saved_courses['url'][i]}\n")

    
    
if __name__ == "__main__" :
    
    parser = ArgumentParser(description='Most popular Udemy courses in your account')
    parser.add_argument('-k', '--keywords', help='courses keywords to filter [ex: python, web dev]', default=' ')
    parser.add_argument('-t', '--top', type=int, help='How many courses to display', default=3)

    args = parser.parse_args()

    main(args)

    
