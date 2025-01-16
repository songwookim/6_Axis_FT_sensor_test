import socket
import time
import sys
import array
import os
import hydra
from omegaconf import DictConfig
from mms101_controller import MMS101Controller



@hydra.main(version_base=None, config_path=".", config_name="config")
def main(config: DictConfig):
    mms_controller = MMS101Controller(config)
    mms_controller.run()




if __name__ == "__main__":
    main()

