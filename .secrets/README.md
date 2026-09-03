# .secrets/

Local secrets — **never committed** (see repository `.gitignore`).

To send email via SMTP without a Cowork connector, put your Gmail **App Password**
(not your normal password) in a file named `smtp_password` here:

    echo "abcd efgh ijkl mnop" > smtp_password

Create an App Password at https://myaccount.google.com/apppasswords
(requires 2-Step Verification enabled on your Google account).

Alternatively, export it as an environment variable instead of using this file:

    export SKY_TONIGHT_SMTP_PASSWORD="abcd efgh ijkl mnop"
