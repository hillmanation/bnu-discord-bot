from email_validator import validate_email, EmailNotValidError


def is_email_valid(email):
    try:
        # Check if the email is valid
        valid_email = validate_email(email)
        # Update with the normalized form of the email
        email = valid_email.normalized
        return True
    except EmailNotValidError as e:
        # Email is not valid, return false
        return e
