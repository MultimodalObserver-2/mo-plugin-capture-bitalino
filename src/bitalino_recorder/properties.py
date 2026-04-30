import os
from mo.core import Properties, PropertySelectOption, Settings, translate

def get_sampling_rate_options() -> list[PropertySelectOption]:
    options = [
        PropertySelectOption(label = "100 Hz", value = 100),
        PropertySelectOption(label = "1000 Hz", value = 1000)
    ]
    return options

def get_properties() -> Properties:
    props = Properties()

    props.add_text("mac_address", translate("com_port"))
    props.set_default("mac_address", "COM10")
    sr_options = get_sampling_rate_options()
    props.add_select("sampling_rate", translate("select_sampling_rate"), sr_options)
    props.set_default("sampling_rate", 1000)
    return props