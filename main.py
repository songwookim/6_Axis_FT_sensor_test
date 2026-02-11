import hydra
from omegaconf import DictConfig
from mms101_controller import MMS101Controller


@hydra.main(version_base=None, config_path=".", config_name="config")
def main(config: DictConfig):
    controller = MMS101Controller(config)
    for i in range(config.mms101.measure_max):
        data = controller.run(i)
        print(data)


if __name__ == "__main__":
    main()