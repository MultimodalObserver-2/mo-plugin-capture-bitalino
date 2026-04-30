import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from bitalino_recorder import properties as props_mod
from mo.core import Properties, PropertySelectOption
from mo.core.plugin.models.properties import PropertyType


class TestProperties(unittest.TestCase):

    def test_sampling_rate_returns_two_options(self):
        opts = props_mod.get_sampling_rate_options()
        self.assertEqual(len(opts), 2)

    def test_sampling_rate_100hz_label(self):
        opts = props_mod.get_sampling_rate_options()
        labels = [o.label for o in opts]
        self.assertIn("100 Hz", labels)

    def test_sampling_rate_100hz_value(self):
        opts = props_mod.get_sampling_rate_options()
        values = [o.value for o in opts]
        self.assertIn(100, values)

    def test_sampling_rate_1000hz_value(self):
        opts = props_mod.get_sampling_rate_options()
        values = [o.value for o in opts]
        self.assertIn(1000, values)

    def test_sampling_rate_options_are_select_option_instances(self):
        opts = props_mod.get_sampling_rate_options()
        for opt in opts:
            self.assertIsInstance(opt, PropertySelectOption)

    def test_get_properties_instance(self):
        props = props_mod.get_properties()
        self.assertIsInstance(props, Properties)

    def test_mac_address_exists(self):
        props = props_mod.get_properties()
        self.assertTrue(props.has_property('mac_address'))

    def test_mac_address_is_text(self):
        props = props_mod.get_properties()
        self.assertEqual(props.get_type('mac_address'), PropertyType.TEXT)

    def test_mac_address_default_is_com10(self):
        props = props_mod.get_properties()
        self.assertEqual(props.get_default_values()['mac_address'], 'COM10')

    def test_sampling_rate_exists(self):
        props = props_mod.get_properties()
        self.assertTrue(props.has_property('sampling_rate'))

    def test_sampling_rate_is_select(self):
        props = props_mod.get_properties()
        self.assertEqual(props.get_type('sampling_rate'), PropertyType.SELECT)

    def test_sampling_rate_default_is_1000(self):
        props = props_mod.get_properties()
        self.assertEqual(props.get_default_values()['sampling_rate'], 1000)

    def test_two_fields_total(self):
        props = props_mod.get_properties()
        defaults = props.get_default_values()
        self.assertEqual(len(defaults), 2)


if __name__ == '__main__':
    unittest.main()
