# Jira-to-Google

This repository contains a script that is designed to synchronize data from Jira to Google Sheets.

The script requires authentication to both Jira and Google Sheets. It leverages Jira's API to pull data and Google Sheets API to push data.

## Usage

Before you can run the Docker image, you will need to have a valid `JIRA_TOKEN` for accessing RISC-V Jira instance, a `GOOGLE_SHEETS_TOKEN` for accessing Google Sheets, and a Google Cloud Service Account JSON key file (`gcp_creds.json`) for authenticating with Google Cloud Platform.

The Docker image can be run using the following command:

```bash
docker run --rm \
    -v $(pwd)/gcp_creds.json:/gcp_creds.json \
    -e JIRA_TOKEN=${JIRA_TOKEN} \
    -e GOOGLE_SHEETS_TOKEN=${GOOGLE_SHEETS_TOKEN} \
    -e GOOGLE_SERVICE_ACCOUNT_CREDENTIALS='/gcp_creds.json' \
    riscvintl/jira-to-google:latest
```

In this command:

- `$(pwd)/gcp_creds.json:/gcp_creds.json` is used to bind-mount the local `gcp_creds.json` file into the Docker container.
- `${JIRA_TOKEN}`, `${GOOGLE_SHEETS_TOKEN}`, and `/gcp_creds.json` are environment variables used to pass your tokens and service account credentials into the Docker container.

The image can be pulled from DockerHub using:

```bash
docker pull riscvintl/jira-to-google:latest
```

Please replace `${JIRA_TOKEN}` and `${GOOGLE_SHEETS_TOKEN}` with your actual tokens and ensure the `gcp_creds.json` file is in the current directory from which you are running the Docker command.

## Contributing

Contributions to improve this project are welcomed. Please feel free to create issues or pull requests.

## License

This project is licensed under the terms of the Apache License 2.0.

