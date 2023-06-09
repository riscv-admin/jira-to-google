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

import csv
import json
import os

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
    jql = 'project = RVG AND (resolution = Unresolved OR resolution = Done) AND \
        issuetype not in subTaskIssueTypes() ORDER BY priority DESC, updated DESC'

    # CSV filename
    csv_filename = 'groups.csv'

    # Open (or create) a CSV file and write data to it
    with open(csv_filename, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Jira URL',
                         'Summary',
                         'Status',
                         'Group Type',
                         'GitHub',
                         'Governing Committee',
                         'Dotted-line Governing Committee',
                         'Group Lifecycle Starting Date',
                         'Creation Date',
                         'Disbanding Date',
                         'Chair',
                         'Chair Starting Date',
                         'Chair End Date',
                         'Vice-chair',
                         'Vice-chair Starting Date',
                         'Vice-chair End Date',
                         'Acting Chair',
                         'Acting Vice-chair'])

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
                        issue.fields.status.name,
                        issue.fields.customfield_10515,  # Group Type
                        issue.fields.customfield_10401,  # GitHub
                        issue.fields.customfield_10402,  # Governing Committee
                        # Dotted-line Governing Committee
                        extract_names(issue.fields.customfield_10516),
                        issue.fields.customfield_10518,  # Group Lifecycle Starting Date
                        issue.fields.customfield_10514,  # Creation Date
                        issue.fields.customfield_10513,  # Disbanding Date
                        issue.fields.customfield_10511,  # Chair
                        issue.fields.customfield_10519,  # Chair Starting Date
                        issue.fields.customfield_10520,  # Chair End Date
                        issue.fields.customfield_10512,  # Vice-chair
                        issue.fields.customfield_10521,  # Vice-chair Starting Date
                        issue.fields.customfield_10522,  # Vice-chair End Date
                        issue.fields.customfield_10509,  # Acting Chair
                        issue.fields.customfield_10510  # Acting Vice-chair
                    ])
            start += len(issues)


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

    # Check if the required environment variables are set
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
    csv_content = get_csv_content('groups.csv')
    creds = get_credentials()
    range_name = get_range_name(csv_content)
    upload_to_google_sheet(csv_content, creds,
                           os.getenv('GOOGLE_SHEETS_TOKEN'),
                           range_name)


if __name__ == '__main__':
    main()
