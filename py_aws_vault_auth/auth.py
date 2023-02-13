from .utils import non_block_read, CHAR_CODE
import json
import subprocess
import sys

AWS_VAULT_CMD = "aws-vault"

AWS_ENV_VARS = ["AWS_ACCESS_KEY_ID",
                "AWS_SECRET_ACCESS_KEY",
                "AWS_SESSION_TOKEN",
                "AWS_SECURITY_TOKEN",
                "AWS_REGION",
                "AWS_DEFAULT_REGION",
                "AWS_VAULT",
                "AWS_SESSION_EXPIRATION",
                "AWS_CREDENTIAL_EXPIRATION",
                ]
"""
Names of environment variables expected.
"""

def input_prompt(message):
    return input(message + "\n")


def stderr_message(message):
    print(message, file=sys.stderr, end="")


def to_boto_auth(aws_vault_credentials):
    """
    Convert the return value of `authenticate(..., return_as=None)` to
    `boto3.Client` parameter values.
    """
    return {
        "aws_access_key_id": aws_vault_credentials["AWS_ACCESS_KEY_ID"],
        "aws_secret_access_key": aws_vault_credentials["AWS_SECRET_ACCESS_KEY"],
        "aws_session_token": aws_vault_credentials["AWS_SESSION_TOKEN"],
        "region_name": aws_vault_credentials["AWS_REGION"],
    }


def to_s3fs_auth(aws_vault_credentials):
    """
    Convert the return value of `authenticate(..., return_as=None)` to
    `s3fs.S3Filesystem` parameter values.
    """
    return {
        # no region here
        "key": aws_vault_credentials["AWS_ACCESS_KEY_ID"],
        "secret": aws_vault_credentials["AWS_SECRET_ACCESS_KEY"],
        "token": aws_vault_credentials["AWS_SESSION_TOKEN"]
    }


def to_environ_auth(aws_vault_credentials):
    """
    Convert the return value of `authenticate(..., return_as=None)` to
    values suitable for `os.environ`.

    This function makes sure only expected `AWS_` variables are set.
    """
    return {
        k: aws_vault_credentials[k] for k in AWS_ENV_VARS
        if k in aws_vault_credentials
    }


def authenticate(profile,
                 prompt="python",
                 return_as=None,
                 aws_vault_cmd=None,
                 **kwargs):
    """
    Authenticates the AWS profile with `aws-vault` and returns the credentials

    The MFA token will only be requested when necessary.

    With the (default) prompt `python`, the MFA token is be requested via
    the python `input` command. That allows the token to be entered inside
    a jupyter notebook context.

    This function adds the prompt method `python` to loop any dialgoues through
    and uses the `terminal` under the hood.

    The authentication is returned as dictionary (i.e. not set as environment
    variables) so multiple profiles can be used easily within one python process.

    Use `return_as` to get parameters immediately usable with boto, pandas or
    use the convenience functions `to_boto_auth` and `to_s3fs_auth` to
    convert the original `aws-vault` credential values.

    :param profile: The name of the AWS profile
    :type profile: str
    :param prompt: (Optional) The mechanism to use to prompt for MFA token
        (e.g. `"python"`, `"osascript"`, `"kdialog"`, `"terminal"`)
    :type prompt: str
    :param return_as: (Optional) The format of authentication data dict
        (e.g. `"boto"`, `"environ"`, `"s3fs"` or `None`)
    :param aws_vault_cmd: name and location of the `aws-vault` command
    :type aws_vault_cmd: str
    :param kwargs: any other arguments will be added as key value pairs to
        the aws-vault arguments, e.g. `region="ap-southeast-2"`, `duration=8h`.
        If the value is `None`, no value is added... e.g. `no-session=None`.

    :returns: the authentication
    :rtype: dict[str,str]

    :raises: subprocess.CalledProcessError
    """

    if aws_vault_cmd is None:
        aws_vault_cmd = AWS_VAULT_CMD

    if prompt == "python":
        kwargs = {**kwargs, "prompt": "terminal"}
    else:
        kwargs = {**kwargs, "prompt": prompt}

    aws_vault_args = []
    for k, v in kwargs.items():
        if v is None:
            aws_vault_args.append(
                f"--{k.replace('_', '-')}")
        else:
            aws_vault_args.extend([
                f"--{k.replace('_', '-')}",
                v])

    # don't use `--json`, but extract from environment
    # so we get the AWS region as well
    aws_vault_process = subprocess.Popen(
        [aws_vault_cmd, "exec",
         *aws_vault_args,
         profile,
         "--",
         sys.executable, "-c",
         "import json, os, sys; json.dump({k: v for k, v in os.environ.items() if k.startswith('AWS_')}, sys.stdout)"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0,
    )

    stderr_data = ""

    if prompt == "python":
        # use threaded read, emulating non-blocking read
        # internally this seems to be a busy wait loop... sorry!
        stderr_stream_read = non_block_read(aws_vault_process.stderr)
        stderr_stream_read.start()

        while stderr_stream_read.is_alive():
            stderr_stream_read.join(0.05)
            stderr_lines = stderr_stream_read.get_completed_lines()
            if stderr_lines:
                stderr_data += stderr_lines
                stderr_message(stderr_lines)
            if stderr_stream_read.is_alive() and stderr_stream_read.read_buffer:
                # incomplete line, probably waiting for a user input
                # expect buffer being written at once, but give it a chance
                stderr_stream_read.join(0.01)
                stderr_lines = stderr_stream_read.get_completed_lines()
                if stderr_lines:
                    stderr_data += stderr_lines
                    stderr_message(stderr_lines)
                if stderr_stream_read.read_buffer.startswith(b"Enter "):
                    # now show a prompt & get the result
                    prompt_text = stderr_stream_read.get_text()
                    response = input_prompt(prompt_text)
                    aws_vault_process.stdin.write(
                        (response+"\n").encode(encoding=CHAR_CODE))

        stderr_stream_read.join()
        stderr_lines = stderr_stream_read.get_text()
        if stderr_lines:
            stderr_data += stderr_lines
            stderr_message(stderr_lines)

    # internally this seems to be a another busy wait loop... sorry!
    aws_vault_process.wait()

    stderr_lines = aws_vault_process.stderr.read().decode(encoding=CHAR_CODE)
    stderr_data += stderr_lines
    stderr_message(stderr_lines)
    stdout_data = aws_vault_process.stdout.read().decode(encoding=CHAR_CODE)

    if aws_vault_process.returncode != 0:
        raise subprocess.CalledProcessError(
            cmd=aws_vault_process.args,
            returncode=aws_vault_process.returncode,
            stderr=stderr_data,
            output=stdout_data,
        )
    aws_vault_credentials = {k: v for k in json.loads(stdout_data).items()
                             if k in AWS_ENV_VARS}

    if return_as in ["boto", "boto3"]:
        return to_boto_auth(aws_vault_credentials)
    elif return_as == "s3fs":
        return to_s3fs_auth(aws_vault_credentials)
    elif return_as in ["env", "environ"]:
        return to_environ_auth(aws_vault_credentials)
    elif return_as in [None, ""]:
        return aws_vault_credentials

    raise ValueError(f"unkonw return type {return_as}")
