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

Script Overview:

This Python script interacts with both the Jira and Google Sheets APIs. It 
fetches data from Jira using a specific Jira Query Language (JQL) and 
uploads the data to a Google Sheets document.

Functions:

- get_data_from_jira(jira_token: str): Fetches data from JIRA with the provided 
JIRA_TOKEN and a pre-specified JQL. The fetched data is saved to a CSV file called 
'specs.csv'.

- find_waiver_granted_labels(labels: List[str]): Returns labels from the provided list 
that contain "granted" or "No Waiver" if no such labels exist.

- next_phase(current_phase: str): Determines the next phase based on the current phase 
of a project. The phases are pre-defined within the function.

- get_csv_content(csv_filepath: str): Reads a CSV file and returns its content as a
 list of rows.

- get_quarter(date: datetime): Calculates the quarter of a provided date.

- get_quarter_year_format(date: datetime): Returns the quarter and last two digits 
of the year in the format 'Q2-23'.

- days_until_end_of_quarter(year: str, quarter: str): Calculates the number of days 
remaining until the end of the given quarter.

- get_credentials(): Retrieves Google API credentials from the environment variable.

- read_csv_file(file_path: str): Reads a CSV file and returns its content as a list of rows.

- get_range_name(values: List[List[Any]]): Calculates the range for Google Sheets based 
on the size of the provided list of values.

- upload_to_google_sheet(values: List[List[Any]], creds: Any, spreadsheet_id: str, range_name: str):
Uploads provided values to a specified Google Sheets document.

- main():
This is the main function that executes the script. It fetches data from Jira, 
reads the fetched data from 'specs.csv', retrieves Google API credentials, calculates 
the range for Google Sheets, and finally, uploads the data to Google Sheets.

The script runs as a standalone program by calling the main() function. The main 
function requires three environment variables: JIRA_TOKEN, GOOGLE_SHEETS_TOKEN, and 
GOOGLE_SERVICE_ACCOUNT_CREDENTIALS. These credentials are used to authenticate and 
authorize the script to access and manipulate data on JIRA and Google Sheets..
"""

import csv
import datetime
import json
import os
import re
import urllib.parse


from datetime import datetime as dt
from google.oauth2 import service_account
from googleapiclient.discovery import build
from jira import JIRA


def get_data_from_jira(jira_token):
    """
    Fetch data from JIRA with given JIRA_TOKEN and JQL (JIRA Query Language)
    """
    jira = JIRA("https://jira.riscv.org",
                token_auth=jira_token)

    # This JQL will return all sub-task type issues which are not completed
    jql = 'project = RVS AND (resolution = Unresolved OR resolution = Done) AND \
        issuetype not in subTaskIssueTypes() ORDER BY priority DESC, updated DESC'

    # CSV filename
    csv_filename = 'specs.csv'

    # Open (or create) a CSV file and write data to it
    with open(csv_filename, 'w', newline='') as file:
        writer = csv.writer(file, quotechar="'", quoting=csv.QUOTE_MINIMAL)
        writer.writerow([
            'Jira URL',
            'Summary',
            'Status',
            'Next Phase',
            'Created',
            'Updated',
            'Due Date',
            'Waivers',
            'Is Fast Track?',
            'ISA or NON-ISA?',
            'Privileged or Unprivileged?',
            'Architecture Review Status',
            'Groups.io',
            'GitHub',
            'Governing Committee',
            'Dotted Line Governing Committee',
            'Public Review',
            'Freeze Topsheet',
            'Ratification-Ready Topsheet',
            'Board Review Planned Approval',
            'Board Review Planned Approval (Quarter-Year)',
            'Days Until Board Review Planned Approval',
            'Next Not Started Sub-Task'
        ])

        start = 0
        while True:
            issues = jira.search_issues(jql, startAt=start, expand='changelog')

            if len(issues) == 0:
                break

            completed_statuses = {
                'Approved',
                'AR Approved',
                'Resolved',
                'Done',
                'Not Required to Freeze',
                'AR Review Not Required',
                'Approval Not Required',
                'Not Required',
                'Not Required for Ratification-Ready',
                'Ecosystem Development Done',
                'Not Required for Ecosystem',
                'Freeze Waiver Granted',
                'Ratification-Ready Waiver Granted'
            }

            for issue in issues:
                if not issue.fields.subtasks:
                    continue

                next_not_started_sub_task = next(
                    (
                        (
                            f"https://jira.riscv.org/browse/{subtask.key}",
                            subtask.fields.summary
                        )
                        for subtask in issue.fields.subtasks
                        if subtask.fields.status.name not in completed_statuses
                    ),
                    (None, None)
                )

                if next_not_started_sub_task[0] is None and next_not_started_sub_task[1] is None:
                    next_not_started_sub_task_name = "There is no next sub-task"
                    next_not_started_sub_task_url = "There is no next sub-task"
                else:
                    next_not_started_sub_task_name = next_not_started_sub_task[1]
                    next_not_started_sub_task_url = next_not_started_sub_task[0]

                if issue.fields.duedate is not None:
                    quarterYear = get_quarter_year_format(
                        datetime.datetime.strptime(issue.fields.duedate, "%Y-%m-%d")
                    )
                else:
                    quarterYear = "Due Date is not set"

                quarter_year_parts = quarterYear.split('-')

                status = issue.fields.status.name
                if status in ['Specification Done', 'Specification Ratified']:
                    daysToBoardApproval = 0
                else:
                    # Ensure quarter_year_parts has at least two 
                    # elements before trying to access them
                    daysToBoardApproval = (
                        "Due Date is not set"
                        if len(quarter_year_parts) < 2
                        else days_until_end_of_quarter(
                            quarter_year_parts[1],
                            quarter_year_parts[0].replace('Q', '')
                        )
                    )

                writer.writerow([
                    f"https://jira.riscv.org/browse/{issue.key}",
                    issue.fields.summary,
                    issue.fields.status.name,
                    next_phase(issue.fields.status.name),
                    str(issue.fields.created).split("T")[0],
                    str(issue.fields.updated).split("T")[0],
                    issue.fields.duedate,
                    find_waiver_granted_labels(issue.fields.labels),  # List Waivers
                    issue.fields.customfield_10406,  # Is Fast Track?
                    issue.fields.customfield_10440,  # ISA or NON-ISA?
                    extract_values(issue.fields.customfield_10528),  # Privileged or Unprivileged?
                    issue.fields.customfield_10523,  # Architecture Review Status
                    issue.fields.customfield_10507,  # Groups.io
                    issue.fields.customfield_10401,  # GitHub
                    extract_values(issue.fields.customfield_10527),  # Governing Committee
                    extract_values(issue.fields.customfield_10516),  # Dotted Line Governing Committee
                    issue.fields.customfield_10508,  # Public Review
                    generate_jira_url(issue.key, 'Freeze', 'Freeze Topsheet'),  # Freeze Topsheet
                    generate_jira_url(issue.key, 'Ratification-Ready', 'Ratification-Ready Topsheet'),  # Ratification-Ready Topsheet
                    issue.fields.customfield_10451,  # Board Review Planned Approval
                    quarterYear,  # Board Review Planned Approval (Quarter-Year)
                    daysToBoardApproval,  # Days until end of quarter
                    generate_next_jira_task_hyperlink(
                        next_not_started_sub_task_url,
                        next_not_started_sub_task_name
                    )
                ])

            start += len(issues)


def extract_values(arr):
    ''''
    This function extracts values from a Jira array field,
    and returns a comma-separated string of values.
    array field = multi-selection list
    '''
    if arr is None:
        return 'None'

    values = [item.value for item in arr]
    
    if not values:  # if list is empty
        return ''
    
    # if list contains only one value or two values, join them appropriately
    if len(values) == 1:
        return values[0]
    if len(values) == 2:
        return ' and '.join(values)
        
    # if list contains more than two values, join all with commas and 'and' before the last one
    return ', '.join(values[:-1]) + ' and ' + values[-1]


def generate_next_jira_task_hyperlink(url, link_text):
    """
    This function generates a Jira URL Hyperlink
    """

    # Define the URL with placeholders for the parent issue key, summary, and link text
    url_template = (
        '=HYPERLINK("{}", "{}")'
    )

    # Format the URL with the provided parent issue key, summary, and link text
    final_url = url_template.format(url, link_text)

    return final_url


def generate_jira_url(parent_issue_key, summary, link_text):
    """
    This function generates a Jira URL with a given JQL query
    """

    notin = 'Freeze' if 'Ratification-Ready' in summary else 'Ratification-Ready'

    # Define the URL with placeholders for the parent issue key, summary, and link text
    url_template = (
        '=HYPERLINK("https://jira.riscv.org/issues/?jql=project%20%3D%20RVS'
        '%20AND%20parent%20%3D%20%22{}%22%20AND%20'
        '(summary%20~%20%22{}%22%20AND%20summary%20!~%20{})'
        '%20ORDER%20BY%20issuetype%20DESC", "{}")'
    )

    # Format the URL with the provided parent issue key, summary, and link text
    final_url = url_template.format(parent_issue_key, summary, notin, link_text)

    return final_url


def find_waiver_granted_labels(labels):
    """
    Use a list comprehension to filter out labels that contain "granted"
    """
    granted_labels = [label for label in labels if "granted" in label.lower()]

    # If the list is not empty, return the labels concatenated
    # by " and ". Otherwise, return "No Waiver".
    if granted_labels:
        return " and ".join(granted_labels)
    else:
        return "No Waiver"


def next_phase(current_phase):
    # Define the phases and their corresponding next phases
    phases = {
        "inception": "Planning",
        "planning": "Development",
        "development": "Freeze",
        "freeze": "Ratification-Ready",
        "ratification-ready": ["Ecosystem Development", "Specification Ratified", "Specification Completed"],
        "specification ratified": ["Ecosystem Development", "Specification Completed"],
        "ecosystem development": "Specification Completed",
        "specification done": "No Next Phase",
    }

    # Transform the current phase to lowercase
    current_phase_lower = current_phase.lower()

    # Find any phase that is in current_phase_lower
    matching_phase_key = next((key for key in phases.keys() if key in current_phase_lower), None)

    if matching_phase_key is not None:
        if matching_phase_key == "ratification-ready" or matching_phase_key == "specification ratified":
            return " or ".join(phases[matching_phase_key])
        else:
            return phases[matching_phase_key]

    raise ValueError(f"Invalid phase: {current_phase}")


def get_csv_content(csv_filepath):
    """
    Read a CSV file and return its content as a list of rows
    """
    with open(csv_filepath, 'r') as csv_file:
        csv_reader = csv.reader(csv_file, quotechar="'")
        return list(csv_reader)


def get_quarter(date):
    """
    Function to calculate the quarter of a given date
    Integer division of (month - 1) by 3 plus 1 gives the quarter
    Example: For June (month = 6), (6-1)//3 + 1 = 2, so June is in Q2
    """
    quarter = (date.month-1)//3 + 1
    return quarter


def get_quarter_year_format(date):
    """
    Function to generate the quarter and year format (e.g., "Q2-23")
    """
    # Check if the date is None
    if date is None:
        return "Date not set, quarter calculation not possible."

    quarter = get_quarter(date)  # Get the quarter
    # Extract the last two digits of the year
    year = str(date.year)[2:]
    # Concatenate 'Q', quarter, '-', and year
    return f"Q{quarter}-{year}"


def days_until_end_of_quarter(year, quarter):
    """
    Function to return the number of days until the end of a given quarter
    or the number of days since the end of a given quarter.
    """
    # Convert year to integer and add the century
    year = int(year) + 2000

    # Define a dictionary to map the quarter to its end month and day
    quarter_end_dates = {1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)}

    try:
        # Get the end date of the given quarter
        end_date = dt(year, *quarter_end_dates[int(quarter)])
    except KeyError:
        # If an invalid quarter number is provided, return an error message
        return "Invalid quarter"

    # Get the current date
    today = dt.now()

    # Calculate the number of days between the end date and today
    remaining_days = (end_date - today).days
    return f"{remaining_days}"


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


def read_csv_file(file_path):
    """
    Function to read a CSV file and return its content as a list of rows.
    """
    with open(file_path, 'r') as csv_file:
        csv_reader = csv.reader(csv_file)
        return list(csv_reader)


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

    return f"Specifications!A1:{letters}{num_rows}"


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

    # Check if the required environment variables are set
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
    csv_content = get_csv_content('specs.csv')
    creds = get_credentials()
    range_name = get_range_name(csv_content)
    upload_to_google_sheet(csv_content, creds,
    os.getenv('GOOGLE_SHEETS_TOKEN'),
    range_name)

if __name__ == '__main__':
    main()
