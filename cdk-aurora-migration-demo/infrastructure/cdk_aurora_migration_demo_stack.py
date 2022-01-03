import configparser
import dataclasses
import functools
import os

import aws_cdk.aws_ec2 as ec2
import aws_cdk.aws_rds as rds
import aws_cdk.aws_ssm as ssm
from aws_cdk import core

@dataclasses.dataclass
class Config():
    """
    Represents the configuration options for this app
    """
    admin_username: str
    admin_password: str

@functools.lru_cache(maxsize=128)
def get_config(path_to_config: str = None) -> Config:
    """
    Returns an instance of the Config class based on reading
    either the default configuration or a config from
    path_to_config if that is supplied.

    :param path_to_config: Storage path of the configuration, defaults to None
    :type path_to_config: str, optional
    :return: Instance of Config
    :rtype: Config
    """

    path_to_config = os.path.join(
        os.path.dirname(__file__),
        "..",
        "configuration.ini"
    )

    cfg = configparser.ConfigParser()
    cfg.read(path_to_config)

    return Config(**cfg["main"])


class SourceDatabaseStack(core.Stack):

    def __init__(self, scope: core.Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        config: Config = get_config()


        
