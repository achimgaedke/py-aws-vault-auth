# py-aws-vault-auth

This is a wrapper for the [`aws-vault` command](https://github.com/99designs/aws-vault)<br/>
This is **not** an interface to the AWS (glacier) vault.

## Introduction

```python3
import py_aws_vault_auth
import boto3

boto_auth = aws_vault_auth.authenticate("DataScience", return_as="boto")
c = boto3.client("s3", **boto_auth)
c.list_objects_v2(Bucket="your-bucket")
```

Looks in a Jupyterlab notebook like this

![py_aws_vault_auth dialogue in Jupyterlab notebook](doc/MFA_JupyterLabNotebook.png)

or in a VSCode notebook like this

![py_aws_vault_auth dialogue in VSCode notebook](doc/MFA_VSCodeNotebook.png)

By the virtue of a context-adjusted version of the builtin [`input` function](
https://docs.python.org/3/library/functions.html#input).

## Project Scope

Make the AWS authentication with the command line tool `aws-vault` easy in an
interactive context different from a terminal, e.g. jupyter notebook.

This project does:

* request the MFA token via python's context, i.e. the `input` function
* returns the context as parameter dictionary directly usable with boto3 or s3fs

If you prefer another window poping up somewhere, you can use `prompt="osascript"`

This project does **not**:

* uses all features of `aws-vault`
* capture the input dialogues for various key chain/password managers

To avoid too many password manager input dialogues, have a look at [the aws-vault documentation](
https://github.com/99designs/aws-vault/blob/master/USAGE.md#backends).

## Project Maturity

This project is born out of need for a smoother integration of devops tools/requirements
with data-science tools. At the moment, it is simply factoring out some code I use
privately. **Please** star this repository if you like it or use the issue
tracker if you have some feedback.

Yes, the thread-based polling of `stderr` is kind of awkward. This was the most
portable way of waiting on output - or it was 6 years ago. I might revisit this
part another time, as OS and backwards-compatibility got better.
(I'm aware of `select` or setting streams to non-blocking mode)

Ah, and tests are missing...

## Installation

No dependencies, just `python3`... and of course [`aws-vault`](https://github.com/99designs/aws-vault)

```sh
pip install git+https://github.com/achimgaedke/py-aws-vault-auth.git
```
