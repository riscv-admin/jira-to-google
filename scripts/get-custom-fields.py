from jira import JIRA

# create a JIRA connection
jira = JIRA("https://jira.riscv.org", token_auth='JIRA_TOKEN')

# get all fields
fields = jira.fields()

# print all custom fields
for field in fields:
    if field['custom']:
        print(f"Field ID: {field['id']}, Field Name: {field['name']}")