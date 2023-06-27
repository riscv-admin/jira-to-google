"""
Copyright [2023] [RISC-V International]

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

    Contributors: Rafael Sene (rafael@riscv.org) - Initial implementation

This script extracts and processes data from a JIRA project using the JIRA API, then
exports this data to a CSV file and finally uploads the CSV data to a Google Sheets
document using the Google Sheets API.

Functions:

- get_data_from_jira: Fetches data from a JIRA project and writes it to a CSV file.

- next_phase: Returns the next expected phase based on the current phase.

- is_leap_year: Checks if a year is a leap year.

- days_since_given_date: Calculates the days elapsed since a given date, converts to 
  years if the total days are equal to or more than a year, considering leap years.

- get_linked_issues: Returns the linked issues for a given issue.

- remaining_days: Calculates the number of days remaining from today to a given date.

- extract_names: Extracts names from a custom JIRA field.

- get_csv_content: Reads a CSV file and returns its content as a list of rows.

- read_csv_file: Reads a CSV file and returns its content as a list of rows.

- get_credentials: Returns Google API credentials from the environment variable.

- get_range_name: Returns the range name based on the size of the data.

- upload_to_google_sheet: Uploads the given data to a Google Sheets document.

The script runs as a standalone program by calling the main() function. The main 
function requires three environment variables: JIRA_TOKEN, GOOGLE_SHEETS_TOKEN, and 
GOOGLE_SERVICE_ACCOUNT_CREDENTIALS. These credentials are used to authenticate and 
authorize the script to access and manipulate data on JIRA and Google Sheets.
"""

import csv
import json
import os

from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from jira import JIRA

#TODO: once the Group sub-tasks are added in Jira, 
# add a function that will return the next not 
# completed sub-task.

def get_data_from_jira(jira_token):
    """
    Fetch data from JIRA with given JIRA_TOKEN and JQL (JIRA Query Language)
    """
    jira = JIRA("https://jira.riscv.org",
                token_auth=jira_token)

    # This JQL will return all sub-task type issues which are not completed
    jql = 'project = RVG AND (resolution = Unresolved OR resolution = Done) AND \
        issuetype not in subTaskIssueTypes() ORDER BY priority DESC, updated DESC'

    # CSV filename
    csv_filename = 'groups.csv'

    # Open (or create) a CSV file and write data to it
    with open(csv_filename, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Jira URL',
                         'Summary',
                         'Group Charter',
                         'Group Current Phase',
                         'Group Next Phase',
                         'Group Type',
                         'Governing Committee',
                         'Dotted-line Governing Committee',
                         'Group Lifecycle Starting Date',
                         'Days since Group Lifecycle Starting Date',
                         'Creation Date',
                         'Disbanding Date',
                         'Chair',
                         'Chair Starting Date',
                         'Chair End Date',
                         'Remaining days for Chair',
                         'Vice-chair',
                         'Vice-chair Starting Date',
                         'Vice-chair End Date',
                         'Remaining days for Vice-chair',
                         'Acting Chair',
                         'Acting Vice-chair',
                         'Linked Specifications'])

        start = 0
        while True:
            issues = jira.search_issues(jql, startAt=start, expand='changelog')

            if len(issues) == 0:
                break

            for issue in issues:
                if not issue.fields.subtasks:
                    writer.writerow([
                        f"https://jira.riscv.org/browse/{issue.key}",
                        issue.fields.summary,
                        issue.fields.customfield_10524,  # Group Charter
                        issue.fields.status.name,
                        next_phase(issue.fields.status.name),  # Group Next Phase
                        issue.fields.customfield_10515,  # Group Type
                        issue.fields.customfield_10402,  # Governing Committee
                        # Dotted-line Governing Committee
                        extract_names(issue.fields.customfield_10516),
                        issue.fields.customfield_10518,  # Group Lifecycle Starting Date
                        # Days since Group Lifecycle Starting Date
                        days_since_given_date(issue.fields.customfield_10518),
                        issue.fields.customfield_10514,  # Creation Date
                        issue.fields.customfield_10513,  # Disbanding Date
                        issue.fields.customfield_10511,  # Chair
                        issue.fields.customfield_10519,  # Chair Starting Date
                        issue.fields.customfield_10520,  # Chair End Date
                        # Remaining days for Chair
                        remaining_days(issue.fields.customfield_10520),
                        issue.fields.customfield_10512,  # Vice-chair
                        issue.fields.customfield_10521,  # Vice-chair Starting Date
                        issue.fields.customfield_10522,  # Vice-chair End Date
                        # Remaining days for Vice-chair
                        remaining_days(issue.fields.customfield_10522),
                        issue.fields.customfield_10509,  # Acting Chair
                        issue.fields.customfield_10510,  # Acting Vice-chair
                        get_linked_issues(issue)  # Linked Specification
                    ])

            start += len(issues)


def next_phase(current_phase):
    phases = {
        'inception': 'Group Kickoff',
        'kickoff': 'Group Formation',
        'formation': 'Group Active',
        'active': 'Group Disbanded',
        'disbanded': 'No Next Phase'
    }

    # Convert current_phase to lower case
    current_phase = current_phase.lower()

    # Check if any phase exists in current_phase
    for phase in phases:
        if phase in current_phase:
            return phases[phase]

    return "No phase found in the current string."


def is_leap_year(year):
    """Check if a year is a leap year."""
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def days_since_given_date(target_date_str=None):
    # return a message if the target date is not set
    if target_date_str is None:
        return "No start date has been set."

    # parse target_date_str to a datetime object
    target_date = datetime.strptime(target_date_str, "%Y-%m-%d")

    # get current date
    current_date = datetime.now()

    # calculate elapsed days
    elapsed = current_date - target_date
    elapsed_days = elapsed.days

    # check if elapsed days are more than or equal to a year
    start_year = target_date.year
    end_year = current_date.year
    total_days_in_years = sum(is_leap_year(year) and 366 or 365 for year in range(start_year, end_year + 1))

    if elapsed_days >= total_days_in_years:
        elapsed_years = elapsed_days // total_days_in_years
        return f"{elapsed_years} years"
    
    return f"{elapsed_days} days"


def get_linked_issues(issue):

    # get the linked issues
    linked_issues = []
    for link in issue.fields.issuelinks:
        if hasattr(link, "outwardIssue"):
            linked_issue = link.outwardIssue
            linked_issue_key = linked_issue.key
            linked_issues.append(f"https://jira.riscv.org/browse/{linked_issue_key}")

    if not linked_issues:
        return "No Specification is linked to the group yet."
    
    # join the list into a single string with each link separated by a newline character
    return "\n ".join(linked_issues)


def remaining_days(target_date_str=None):
    # return a message if the target date is not set
    if target_date_str is None:
        return "No end date has been set."

    # parse target_date_str to a datetime object
    target_date = datetime.strptime(target_date_str, "%Y-%m-%d")

    # get current date
    current_date = datetime.now()

    # calculate remaining days
    remaining = target_date - current_date

    # return the number of days (rounded to nearest day)
    return round(remaining.total_seconds() / (24 * 60 * 60))


def extract_names(custom_field_options):
    names = []

    for option in custom_field_options:
        if option is not None:  # Make sure the option is not None before extracting value
            names.append(option.value)
    clean_names = ', '.join(names)
    return clean_names


def get_csv_content(csv_filepath):
    """
    Read a CSV file and return its content as a list of rows
    """
    with open(csv_filepath, 'r') as csv_file:
        csv_reader = csv.reader(csv_file)
        return list(csv_reader)


def read_csv_file(file_path):
    """
    Function to read a CSV file and return its content as a list of rows.
    """
    with open(file_path, 'r') as csv_file:
        csv_reader = csv.reader(csv_file)
        return list(csv_reader)


def get_credentials():
    """
    Function to get Google API credentials from the environment variable.
    Returns the credentials object.
    """
    creds_info = os.getenv('GOOGLE_SERVICE_ACCOUNT_CREDENTIALS')
    creds_json = json.loads(creds_info)
    creds = service_account.Credentials.from_service_account_info(creds_json)

    # If modifying the scopes, delete the token.json file
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
              'https://www.googleapis.com/auth/drive']
    scoped_creds = creds.with_scopes(SCOPES)

    return scoped_creds


def get_range_name(values):
    """
    Function to get the range name based on the size of the data.
    """
    num_rows = len(values)
    num_cols = len(values[0]) if values else 0

    # Convert the column number to a column letter
    # (e.g., 1 -> A, 2 -> B, ..., 26 -> Z, 27 -> AA, ...)
    letters = ""
    while num_cols:
        num_cols, remainder = divmod(num_cols - 1, 26)
        letters = chr(65 + remainder) + letters

    return f"Groups!A1:{letters}{num_rows}"


def upload_to_google_sheet(values, creds, spreadsheet_id, range_name):
    """
    Function to upload the given values to Google Sheets.
    """
    service = build('sheets', 'v4', credentials=creds)

    body = {
        'values': values
    }

    # Call the Sheets API
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=range_name,
        valueInputOption="USER_ENTERED",
        body=body
    ).execute()


def main():
    """
    The main function to run the whole script
    """

    #Check if the required environment variables are set
    if not all([os.getenv('JIRA_TOKEN'), os.getenv('GOOGLE_SHEETS_TOKEN'), \
            os.getenv('GOOGLE_SERVICE_ACCOUNT_CREDENTIALS')]):
        raise EnvironmentError("""
            Error: Required environment variables are not set.
            Please check your:
            - JIRA_TOKEN
            - GOOGLE_SHEETS_TOKEN
            - GOOGLE_SERVICE_ACCOUNT_CREDENTIALS
        """)

    get_data_from_jira(os.getenv('JIRA_TOKEN'))
    csv_content = get_csv_content('groups.csv')
    creds = get_credentials()
    range_name = get_range_name(csv_content)
    upload_to_google_sheet(csv_content, creds,
                           os.getenv('GOOGLE_SHEETS_TOKEN'),
                           range_name)


if __name__ == '__main__':
    main()
