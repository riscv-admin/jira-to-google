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
"""

from jira import JIRA
import datetime

from google.oauth2 import service_account
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

import csv
import os
import json


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
        writer = csv.writer(file)
        writer.writerow(['Jira URL', 
        'Summary', 'Status', 'Created', 
        'Updated', 'Due Date', 'Is Fast Track?', 
        'ISA or NON-ISA?', 'Groups.io', 'GitHub','Governing Committee', 
        'Public Review', 'Board Review Planned Approval', 
        'Board Review Planned Approval (Quarter-Year)',
        'Next Not Started Sub-Task Name', 
        'Next Not Started Sub-Task URL'])

        start = 0
        while True:
            issues = jira.search_issues(jql, startAt=start, expand='changelog')

            if len(issues) == 0:
                break

            completed_statuses = {'Approved','AR Approved','Resolved','Done',
            'Not Required to Freeze','AR Review Not Required','Not Required',
            'Not Required for Ratification-Ready','Ecosystem Development Done',
            'Not Required for Ecosystem', 'Freeze Waiver Granted', 
            'Ratification-Ready Waiver Granted'}

            for issue in issues:
                if not issue.fields.subtasks:
                    continue

                next_not_started_sub_task = next(((f"https://jira.riscv.org/browse/{subtask.key}", 
                subtask.fields.summary) 
                                                for subtask in issue.fields.subtasks 
                                                if subtask.fields.status.name not in 
                                                completed_statuses), 
                                                (None, None))

                if next_not_started_sub_task[0] is None and \
                    next_not_started_sub_task[1] is None:
                    next_not_started_sub_task_name = "There is no next sub-task"
                    next_not_started_sub_task_url = "There is no next sub-task"
                else:
                    next_not_started_sub_task_name = next_not_started_sub_task[1]
                    next_not_started_sub_task_url = next_not_started_sub_task[0]

                writer.writerow([
                    f"https://jira.riscv.org/browse/{issue.key}",
                    issue.fields.summary,
                    issue.fields.status.name,
                    str(issue.fields.created).split("T")[0],
                    str(issue.fields.updated).split("T")[0],
                    issue.fields.duedate,
                    issue.fields.customfield_10406, # Is Fast Track?
                    issue.fields.customfield_10440, # ISA or NON-ISA?
                    issue.fields.customfield_10507, # Groups.io
                    issue.fields.customfield_10401, # GitHub
                    issue.fields.customfield_10402, # Governing Committee
                    issue.fields.customfield_10508, # Public Review
                    issue.fields.customfield_10451, # Board Review Planned Approval
                    get_quarter_year_format(datetime.datetime.strptime
                    (issue.fields.duedate, "%Y-%m-%d")), # Board Review Planned Approval (Quarter-Year)
                    next_not_started_sub_task_name, # Next Not Started Sub-Task Name
                    next_not_started_sub_task_url # Next Not Started Sub-Task URL
                ])
            start += len(issues)


def get_csv_content(csv_filepath):
    """
    Read a CSV file and return its content as a list of rows
    """
    with open(csv_filepath, 'r') as csv_file:
        csv_reader = csv.reader(csv_file)
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
    quarter = get_quarter(date)  # Get the quarter
    # Extract the last two digits of the year
    year = str(date.year)[2:]
    # Concatenate 'Q', quarter, '-', and year
    return f"Q{quarter}-{year}"


def get_credentials():
    """
    Function to get Google API credentials from the service account file.
    Returns the credentials object.
    """
    creds = Credentials.from_service_account_file('gcp_creds.json')

    # If modifying the scopes, delete the token.json file
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 
    'https://www.googleapis.com/auth/drive']
    scoped_creds = creds.with_scopes(SCOPES)

    return scoped_creds


# def get_credentials():
#     """
#     Function to get Google API credentials from the environment variable.
#     Returns the credentials object.
#     """
#     creds_info = os.getenv('GOOGLE_SERVICE_ACCOUNT_CREDENTIALS')
#     creds_json = json.loads(creds_info)
#     creds = service_account.Credentials.from_service_account_info(creds_json)

#     # If modifying the scopes, delete the token.json file
#     SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
#     'https://www.googleapis.com/auth/drive']
#     scoped_creds = creds.with_scopes(SCOPES)

#     return scoped_creds


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
    # Define your JIRA API token
    get_data_from_jira(os.getenv('JIRA_TOKEN'))
    csv_content = get_csv_content('specs.csv')
    creds = get_credentials()
    range_name = get_range_name(csv_content)
    upload_to_google_sheet(csv_content, creds,
    os.getenv('GOOGLE_SHEETS_TOKEN'),
    range_name)


if __name__ == '__main__':
    main()
