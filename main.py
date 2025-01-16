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

# Sensor 1: [8.359, 2.19, -10.648, 0.02246, -0.03812, -0.00082]
# Sensor 2: [0.152, -0.718, -21.906, -0.03203, 0.00802, 0.00272]
# Sensor 3: [0.868, -6.551, -38.799, -0.04005, -0.01295, -0.00334]

# Sensor 1: [8.35, 2.228, -10.601, 0.02237, -0.03813, -0.00122]
# Sensor 2: [0.126, -0.707, -21.922, -0.03217, 0.00784, 0.00171]
# Sensor 3: [0.893, -6.534, -38.767, -0.03998, -0.01291, -0.00256]