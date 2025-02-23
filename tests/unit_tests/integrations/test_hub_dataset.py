import pytest

from unit_tests.base import TestBase
from unit_tests.utils import is_package_installed


class TestHubDatasetIntegration(TestBase):
    @pytest.mark.skipif(not is_package_installed('hub'), reason="'hub' is not installed. skipping.")
    def test_dataset_as_run_param(self):
        import hub

        from aimstack.ml.models.hub_dataset import HubDataset
        from aim.sdk import Run

        # create dataset object
        ds = hub.dataset('hub://activeloop/cifar100-test')

        # log dataset metadata
        run = Run(system_tracking_interval=None)
        run['hub_ds'] = HubDataset(ds)

        # get dataset metadata
        ds_object = run['hub_ds']
        ds_dict = run.get('hub_ds', resolve_objects=True)

        self.assertTrue(isinstance(ds_object, HubDataset))
        self.assertTrue(isinstance(ds_dict, dict))
        self.assertIn('meta', ds_dict['dataset'].keys())
        self.assertIn('source', ds_dict['dataset'].keys())
