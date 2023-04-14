# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
# --------------------------------------------------------------------------
from pathlib import Path
from typing import Callable, Union

from pydantic import validator

from olive.common.config_utils import ConfigBase, ConfigParam, create_config_class

WARMUP_NUM = 10
REPEAT_TEST_NUM = 20
SLEEP_NUM = 0


_common_user_config = {
    "script_dir": ConfigParam(type_=Union[Path, str]),
    "user_script": ConfigParam(type_=Union[Path, str]),
    "data_dir": ConfigParam(type_=Union[Path, str]),
    "batch_size": ConfigParam(type_=int, default_value=1),
}

_common_user_config_validators = {}

_type_to_user_config = {
    "latency": {
        "dataloader_func": ConfigParam(type_=Union[Callable, str], required=True, is_object=True),
        "inference_settings": ConfigParam(type_=dict),
        "io_bind": ConfigParam(type_=bool, default_value=False),
    },
    "accuracy": {
        "dataloader_func": ConfigParam(type_=Union[Callable, str], required=True, is_object=True),
        "post_processing_func": ConfigParam(type_=Union[Callable, str], is_object=True),
        "inference_settings": ConfigParam(type_=dict),
    },
    "custom": {
        "evaluate_func": ConfigParam(type_=Union[Callable, str], required=True, is_object=True),
    },
}

_type_to_user_config_validators = {}


def get_user_config_class(metric_type: str):
    default_config = _common_user_config.copy()
    default_config.update(_type_to_user_config[metric_type])
    validators = _common_user_config_validators.copy()
    validators.update(_type_to_user_config_validators.get(metric_type, {}))
    return create_config_class(f"{metric_type.title()}UserConfig", default_config, ConfigBase, validators)


# TODO: automate latency metric config also we standardize accuracy metric config
class LatencyMetricConfig(ConfigBase):
    warmup_num: int = WARMUP_NUM
    repeat_test_num: int = REPEAT_TEST_NUM
    sleep_num: int = SLEEP_NUM


class MetricGoal(ConfigBase):
    type: str  # threshold , deviation, percent-deviation
    value: float

    @validator("type")
    def check_type(cls, v):
        allowed_types = [
            "threshold",
            "min-improvement",
            "percent-min-improvement",
            "max-degradation",
            "percent-max-degradation",
        ]
        if v not in allowed_types:
            raise ValueError(f"Metric goal type must be one of {allowed_types}")
        return v

    @validator("value")
    def check_value(cls, v, values):
        if "type" not in values:
            raise ValueError("Invalid type")
        if values["type"] in ["min-improvement", "max-degradation"] and v < 0:
            raise ValueError(f"Value must be positive for type {values['type']}")
        return v