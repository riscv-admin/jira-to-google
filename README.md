# Jira-to-Google

This repository contains a script that is designed to synchronize data from Jira to Google Sheets.

The script requires authentication to both Jira and Google Sheets. It leverages Jira's API to pull data and Google Sheets API to push data.

## Usage

Before you can run the Docker image, you will need to have a valid `JIRA_TOKEN` for accessing RISC-V Jira instance, a `GOOGLE_SHEETS_TOKEN` for accessing Google Sheets, and a Google Cloud Service Account JSON (`GOOGLE_SERVICE_ACCOUNT_CREDENTIALS`) for authenticating with Google Cloud Platform.

The Docker image can be run using the following command:

```bash
# Specifications
docker run --rm \
        -e JIRA_TOKEN=${{ secrets.JIRA_TOKEN }} \
        -e GOOGLE_SHEETS_TOKEN=${{ secrets.GOOGLE_SHEETS_TOKEN }} \
        -e GOOGLE_SERVICE_ACCOUNT_CREDENTIALS='${{ secrets.GOOGLE_SERVICE_ACCOUNT_CREDENTIALS }}' \
        riscvintl/specs-to-google:latest

# Groups
docker run --rm \
        -e JIRA_TOKEN=${{ secrets.JIRA_TOKEN }} \
        -e GOOGLE_SHEETS_TOKEN=${{ secrets.GOOGLE_SHEETS_TOKEN }} \
        -e GOOGLE_SERVICE_ACCOUNT_CREDENTIALS='${{ secrets.GOOGLE_SERVICE_ACCOUNT_CREDENTIALS }}' \
        riscvintl/groups-to-google:latest
```

The image can be pulled from DockerHub using:

```bash
docker pull riscvintl/groups-to-google:latest
docker pull riscvintl/specs-to-google:latest
```

## Contributing

Contributions to improve this project are welcomed. Please feel free to create issues or pull requests.

## License

This project is licensed under the terms of the Apache License 2.0.
