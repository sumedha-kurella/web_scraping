import pandas as pd
from random import randint
from time import sleep
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from webdriver_manager.chrome import ChromeDriverManager
import os
import re

def generate_url_naukri(job_title, index):
    if index == 1:
        return f"https://www.naukri.com/{job_title}-jobs-in-india"
    else:
        return f"https://www.naukri.com/{job_title}-jobs-in-india-{index}"

def extract_date_posted_naukri(row6):
    span = row6.find('span', class_="job-post-day")
    return span.text.strip() if span else 'Not specified'

def extract_url_naukri(row1):
    anchor = row1.find('a', class_='title')
    return anchor['href'] if anchor else 'Not specified'

def extract_salary_naukri(row3):
    span = row3.find('span', class_="sal-wrap")
    return span.text.strip() if span else 'Not specified'

def parse_job_data_from_soup_naukri(page_jobs, df):
    data = []
    for job in page_jobs:
        job = BeautifulSoup(str(job), 'html.parser')
        row1 = job.find('div', class_="row1")
        row2 = job.find('div', class_="row2")
        row3 = job.find('div', class_="row3")
        row4 = job.find('div', class_="row4")
        row5 = job.find('div', class_="row5")
        row6 = job.find('div', class_="row6")

        job_title = row1.a.text
        company_name = row2.span.a.text

        exp_wrap = row3.find('span', class_="exp-wrap").text.strip() if row3.find('span', class_="exp-wrap") else 'Not specified'

        salary = extract_salary_naukri(row3)
        date_posted = extract_date_posted_naukri(row6)
        url = extract_url_naukri(row1)

        location_span = row3.find('span', class_='loc')
        location = location_span.text.strip() if location_span else 'Not specified'

        skills_ul = row5.find('ul', class_='tags-gt')
        skills = ', '.join([li.text.strip() for li in skills_ul.find_all('li')]) if skills_ul else 'Not specified'

        data.append({'Id': '', 'Job Title': job_title, 'Company Name': company_name, 'Experience': exp_wrap,
                     'Salary': salary, 'Date Posted': date_posted,  'Location': location, 'Skills': skills, 'URL': url})

    return pd.concat([df, pd.DataFrame(data)], ignore_index=True)

def scrape_naukri_data(job_titles, page_limit):
    df_naukri = pd.DataFrame(columns=['Id','Job Title', 'Company Name', 'Experience', 'Salary', 'Date Posted','Location', 'Skills', 'URL'])

    options = webdriver.ChromeOptions() 
    options.headless = True 
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    for job_title in job_titles:
        index = 1
        while index <= page_limit:
            url = generate_url_naukri(job_title, index)
            driver.get(url)
            sleep(randint(5, 10))
            get_url = driver.current_url

            if get_url != url:
                break

            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            page_jobs = soup.find_all("div", class_="srp-jobtuple-wrapper")

            if not page_jobs:
                break  # No jobs found on this page, move to next job title

            df_naukri = parse_job_data_from_soup_naukri(page_jobs, df_naukri)
            index += 1

    driver.quit()
    return df_naukri

def generate_url_timesjobs(job_title, page_num):
    base_url = "https://www.timesjobs.com/candidate/job-search.html"
    params = {
        "from": "submit",
        "luceneResultSize": 25,
        "txtKeywords": job_title,
        "postWeek": 60,
        "searchType": "personalizedSearch",
        "actualTxtKeywords": job_title,
        "searchBy": 0,
        "rdoOperator": "OR",
        "txtLocation": "India",
        "pDate": "I",
        "sequence": page_num,
        "startPage": 1
    }
    url = base_url + "?" + "&".join([f"{key}={value}" for key, value in params.items()])
    return url

def extract_data_timesjobs(job):
    title = job.find('a').text.strip()
    company = job.find('h3', class_='joblist-comp-name').text.strip()
    experience = job.find('ul', class_='top-jd-dtl clearfix').find('li').contents[-1]
    
    location_li = job.find('ul', class_='top-jd-dtl clearfix').find_all('li')
    location_span = location_li[1].find('span') if len(location_li) > 1 else None
    location = location_span.text.strip() if location_span else 'Not specified'
    
    skills_li = job.find('ul', class_='list-job-dtl clearfix').find_all('li')
    skills = skills_li[1].find('span', class_='srp-skills').text.strip() if len(skills_li) > 1 and skills_li[1].find('span', class_='srp-skills') else 'Not specified'
    
    salary = job.find('i', class_='material-icons rupee').next_sibling.strip() if job.find('i', class_='material-icons rupee') else 'Not Mentioned'
    
    date_posted = job.find('span', class_='sim-posted').text.strip()
    date_posted = re.sub(r'posted', '', date_posted, flags=re.IGNORECASE).strip()    
    
    url = job.find('a')['href']

    return title, company, experience, location, skills, salary, date_posted, url

def scrape_timesjobs_data(job_titles, page_limit):
    df_timesjobs = pd.DataFrame(columns=['Job Title', 'Company Name', 'Experience', 'Location', 'Skills', 'Salary', 'Date Posted', 'URL'])
    driver = webdriver.Chrome()

    for job_title in job_titles:
        page_num = 1
        while page_num <= page_limit:
            url = generate_url_timesjobs(job_title, page_num)
            driver.get(url)
            sleep(randint(5, 10))

            try:
                driver.find_element(By.ID, 'closeSpanId').click()
            except:
                pass

            soup = BeautifulSoup(driver.page_source, 'html.parser')
            job_listings = soup.find_all('li', class_='clearfix job-bx wht-shd-bx')

            if not job_listings:
                break  # No jobs found on this page, move to next job title

            data = []
            for job in job_listings:
                title, company, experience, location, skills, salary, date_posted, job_url = extract_data_timesjobs(job)
                data.append({'Job Title': title, 'Company Name': company, 'Experience': experience,
                             'Location': location, 'Skills': skills, 'Salary': salary, 'Date Posted': date_posted,
                             'URL': job_url})

            df_timesjobs = pd.concat([df_timesjobs, pd.DataFrame(data)], ignore_index=True)
            page_num += 1

            if page_num > page_limit:
                break

    driver.quit()
    return df_timesjobs

def generate_url_foundit(job_role, start=0, limit=15):
    return f"https://www.foundit.in/srp/results?start={start}&sort=1&limit={limit}&query={job_role}&queryDerived=true"

def generate_job_url(job):
    title = job['Job Title'].lower().replace(' ', '-')
    company = job['Company Name'].lower().replace(' ', '-')
    location = job['Location'].lower().replace(' ', '-')
    job_id = job['Job ID']
    
    # Replace special characters and spaces with hyphens
    title = re.sub(r'[^a-zA-Z0-9]', '-', title)
    company = re.sub(r'[^a-zA-Z0-9]', '-', company)
    location = re.sub(r'[^a-zA-Z0-9]', '-', location)
    
    return f"https://www.foundit.in/job/{title}-{company}-{location}-{job_id}"

def extract_data_foundit(job):
    # Job Title and Company Name
    title_element = job.find('div', class_='jobTitle')
    title = title_element.text.strip() if title_element else 'Not specified'

    company_element = job.find('div', class_='companyName')
    company = company_element.text.strip() if company_element else 'Not specified'

    # Location
    location_element = job.find_all('div', class_='bodyRow')[1].find('div', class_='details').text.strip()
    location = location_element if location_element else 'Not specified'

    # Experience
    experience_element = job.find_all('div', class_='bodyRow')[2].find('div', class_='details').text.strip()
    experience = experience_element if experience_element else 'Not specified'

    # Skills
    skills_element = job.find('div', class_='skillDetails')
    if skills_element:
        skills = ', '.join([skill.text.strip() for skill in skills_element.find_all('div', class_='skillTitle')])
    else:
        skills = 'Not specified'

    # Salary - Not provided in the provided HTML elements
    salary = 'Not specified'

    # Date Posted
    date_posted_element = job.find('div', class_='jobAddedTime').find('p', class_='timeText').text.strip()
    date_posted = date_posted_element if date_posted_element else 'Not specified'

    # Extract job ID
    job_id_element = job.get('id')
    job_id = job_id_element if job_id_element else 'Not specified'

    # Generate URL
    job_url = generate_job_url({'Job Title': title, 'Company Name': company, 'Location': location, 'Job ID': job_id})
    
    return title, company, experience, location, skills, salary, date_posted, job_id, job_url


def scrape_foundit_data(job_roles, pages):
    driver = webdriver.Chrome()
    df_foundit = pd.DataFrame(columns=['Id','Job Title', 'Company Name', 'Experience', 'Location', 'Skills', 'Salary', 'Date Posted', 'URL'])
    id_counter = 1  # Initialize ID counter
    for job_role in job_roles:  # Iterate over all specified job roles
        for page in range(pages):
            start = page * 15
            url = generate_url_foundit(job_role, start)
            driver.get(url)
            sleep(5)  # Let the page load

            soup = BeautifulSoup(driver.page_source, 'html.parser')
            job_listings = soup.find_all('div', class_='cardContainer')

            if not job_listings:
                break  # No jobs found on this page, move to the next page

            data = []
            for job in job_listings:
                title, company, experience, location, skills, salary, date_posted, job_id, job_url = extract_data_foundit(job)
                data.append({'Id': id_counter,'Job Title': title, 'Company Name': company, 'Experience': experience,
                             'Location': location, 'Skills': skills, 'Salary': salary,
                             'Date Posted': date_posted, 'URL': job_url})
                id_counter += 1  # Increment ID counter

            df_foundit = pd.concat([df_foundit, pd.DataFrame(data)], ignore_index=True)
            df_foundit.to_csv('scraping_ntf.csv', mode='a', header=False, index=False)

    driver.quit()
    return df_foundit


def update_jobs_data_foundit(job_roles, pages):
    for job_role in job_roles:
        # Scrape and save updated data
        df_foundit = scrape_foundit_data(job_role, pages)

def merge_jobs_data():
    job_titles = ["software-engineer", "data-scientist","java-developer", "python-developer", "frontend-developer", "backend-developer", "product-analyst", "Account-Manager"]
    page_limit = 10

    # Scrape data from Naukri.com
    naukri_df = scrape_naukri_data(job_titles, page_limit)

    # Scrape data from TimesJobs.com
    timesjobs_df = scrape_timesjobs_data(job_titles, page_limit)

    # Scrape data from Foundit.in
    foundit_df = scrape_foundit_data(job_titles, page_limit)

    # Append Id column to each dataframe
    naukri_df['Id'] = range(1, len(naukri_df) + 1)
    timesjobs_df['Id'] = range(len(naukri_df) + 1, len(naukri_df) + 1 + len(timesjobs_df))
    foundit_df['Id'] = range(len(naukri_df) + len(timesjobs_df) + 1, len(naukri_df) + len(timesjobs_df) + 1 + len(foundit_df))

    # Merge dataframes
    merged_df = pd.concat([naukri_df, timesjobs_df, foundit_df], ignore_index=True)

    # Reorder columns to have Id as the first column
    merged_df = merged_df[['Id', 'Job Title', 'Company Name', 'Experience', 'Salary', 'Date Posted', 'Location', 'Skills', 'URL']]

    # Save merged data to CSV
    merged_df.to_csv('scraping_ntf.csv', mode='w', index=False)

def update_jobs_data():
    # Merge and save updated data
    merge_jobs_data()

if __name__ == "__main__":
    update_jobs_data()
