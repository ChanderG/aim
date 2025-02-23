import os

from unit_tests.base import TestBase

from aim.sdk import Run
from aim.sdk.context import Context
from aim.core.storage.hashing import hash_auto


class TestRunContainerData(TestBase):
    def test_meta_tree_contexts_and_names(self):
        train_context = {'subset': 'train'}
        val_context = {'subset': 'val'}
        empty_context = {}

        run = Run(repo=self.repo, system_tracking_interval=None)
        run.track(1.0, name='metric 1', context=train_context)
        run.track(1.0, name='metric 2', context=train_context)
        run.track(1.0, name='metric 1', context=val_context)
        run.track(1.0, name='metric 2', context=val_context)
        run.track(1.0, name='metric 3', context=val_context)
        run.track(0.0, name='metric')

        tree = self.repo.get_meta_tree(read_only=True)

        contexts = tree['contexts']
        for ctx in [train_context, val_context, empty_context]:
            self.assertIn(Context(ctx).idx, contexts)
            self.assertDictEqual(contexts[Context(ctx).idx], ctx)

        self.assertTrue({'float'}.issubset(set(tree.view('traces_types').keys())))
        metric_traces = tree.view(('traces_types', 'float', Context(train_context).idx)).collect()
        self.assertTrue({'metric 1', 'metric 2'}.issubset(set(metric_traces.keys())))
        metric_traces = tree.view(('traces_types', 'float', Context(val_context).idx)).collect()
        self.assertTrue({'metric 1', 'metric 2', 'metric 3'}.issubset(set(metric_traces.keys())))
        metric_traces = tree.view(('traces_types', 'float', Context(empty_context).idx)).collect()
        self.assertTrue({'metric'}.issubset(set(metric_traces.keys())))

    def test_meta_run_tree_contexts_and_names(self):
        train_context = {'subset': 'train'}
        val_context = {'subset': 'val'}
        empty_context = {}

        run = Run(repo=self.repo, system_tracking_interval=None)
        run.track(1, name='metric 1', context=train_context)
        run.track(1, name='metric 2', context=train_context)
        run.track(1, name='metric 1', context=val_context)
        run.track(1, name='metric 2', context=val_context)
        run.track(1, name='metric 3', context=val_context)
        run.track(0, name='metric')

        tree = self.repo.get_meta_tree(read_only=True)

        contexts = tree.view(('chunks', run.hash, 'contexts')).collect()
        for ctx in [train_context, val_context, empty_context]:
            self.assertIn(Context(ctx).idx, contexts)
            self.assertDictEqual(contexts[Context(ctx).idx], ctx)

        traces = tree.view(('chunks', run.hash, 'traces', Context(train_context).idx)).collect()
        self.assertSetEqual({'metric 1', 'metric 2'}, set(traces.keys()))
        traces = tree.view(('chunks', run.hash, 'traces', Context(val_context).idx)).collect()
        self.assertSetEqual({'metric 1', 'metric 2', 'metric 3'}, set(traces.keys()))
        traces = tree.view(('chunks', run.hash, 'traces', Context(empty_context).idx)).collect()
        self.assertSetEqual({'metric'}, set(traces.keys()))

    def test_run_trace_dtype_and_last_value(self):
        run = Run()
        run.track(1.0, name='metric 1', context={})
        run.track(2.0, name='metric 1', context={})
        run.track(3.0, name='metric 1', context={})
        run.track(1.0, name='metric 1', context={'subset': 'train'})

        tree = self.repo.get_meta_tree(read_only=True)
        metric_1_dict = tree.view(('chunks', run.hash, 'traces', Context({}).idx, 'metric 1')).collect()
        self.assertEqual(3.0, metric_1_dict['last'])
        self.assertEqual('float', metric_1_dict['dtype'])

        metric_1_dict = tree.view(('chunks', run.hash, 'traces',
                                   Context({'subset': 'train'}).idx, 'metric 1')).collect()
        self.assertEqual(1.0, metric_1_dict['last'])

    def test_series_tree_values(self):
        # sequential steps
        run = Run()
        run.track(1.0, name='metric 1', context={})
        run.track(2.0, name='metric 1', context={})
        run.track(3.0, name='metric 1', context={})

        tree = self.repo.get_sequence_tree(read_only=True)
        trace = tree.view(('v2', 'chunks', run.hash, Context({}).idx, 'metric 1'))
        self.assertSetEqual({'step', 'val', 'epoch', 'time'}, set(trace.keys()))
        steps = sorted(trace.array('step').values_list())
        vals = trace.array('val').values_list()
        epochs = trace.array('epoch').values_list()
        times = trace.array('time').values_list()

        self.assertEqual(3, len(steps))
        self.assertEqual(3, len(vals))
        self.assertEqual(3, len(epochs))
        self.assertEqual(3, len(times))

        self.assertListEqual([0, 1, 2], steps)
        self.assertEqual(1.0, trace.array('val')[hash_auto(steps[0])])
        self.assertEqual(2.0, trace.array('val')[hash_auto(steps[1])])
        self.assertEqual(3.0, trace.array('val')[hash_auto(steps[2])])

        # user-specified steps
        run = Run()
        run.track(1.0, name='metric 1', step=10, context={})
        run.track(2.0, name='metric 1', step=20, context={})
        run.track(3.0, name='metric 1', step=30, context={})

        tree = self.repo.get_sequence_tree(read_only=True)
        trace = tree.view(('v2', 'chunks', run.hash, Context({}).idx, 'metric 1'))
        steps = sorted(trace.array('step').values_list())
        vals = trace.array('val').values_list()
        epochs = trace.array('epoch').values_list()
        times = trace.array('time').values_list()

        self.assertEqual(3, len(steps))
        self.assertEqual(3, len(vals))
        self.assertEqual(3, len(epochs))
        self.assertEqual(3, len(times))

        self.assertListEqual([10, 20, 30], steps)
        self.assertEqual(1.0, trace.array('val')[hash_auto(steps[0])])
        self.assertEqual(2.0, trace.array('val')[hash_auto(steps[1])])
        self.assertEqual(3.0, trace.array('val')[hash_auto(steps[2])])

        # user-specified steps, unordered
        run = Run()
        run.track(3.0, name='metric 1', step=30, context={})
        run.track(1.0, name='metric 1', step=10, context={})
        run.track(2.0, name='metric 1', step=20, context={})

        tree = self.repo.get_sequence_tree(read_only=True)
        trace = tree.view(('v2', 'chunks', run.hash, Context({}).idx, 'metric 1'))
        steps = sorted(trace.array('step').values_list())
        vals = trace.array('val').values_list()
        epochs = trace.array('epoch').values_list()
        times = trace.array('time').values_list()

        self.assertEqual(3, len(steps))
        self.assertEqual(3, len(vals))
        self.assertEqual(3, len(epochs))
        self.assertEqual(3, len(times))

        self.assertListEqual([10, 20, 30], steps)
        self.assertEqual(1.0, trace.array('val')[hash_auto(steps[0])])
        self.assertEqual(2.0, trace.array('val')[hash_auto(steps[1])])
        self.assertEqual(3.0, trace.array('val')[hash_auto(steps[2])])

    def test_run_set_param_meta_tree(self):
        run = Run()
        run['p1'] = 1
        run['p2'] = {'foo': 'bar'}
        run['p3'] = 0.0
        run['p4'] = True
        run['p5'] = ['x', 1, 2]
        run['p6'] = None
        run['p7'] = 'bazե\x00a-a'
        run['p8'] = b'blob'

        tree = self.repo.get_meta_tree(read_only=True)
        meta_attrs_tree = tree.view(('attrs'))
        meta_run_attrs_tree = tree.view(('chunks', run.hash, 'attrs'))

        val = meta_attrs_tree['p1']
        self.assertEqual(int, type(val))
        self.assertEqual(1, val)

        val = meta_run_attrs_tree['p1']
        self.assertEqual(int, type(val))
        self.assertEqual(1, val)

        val = meta_attrs_tree['p3']
        self.assertEqual(float, type(val))
        self.assertEqual(0.0, val)

        val = meta_run_attrs_tree['p3']
        self.assertEqual(float, type(val))
        self.assertEqual(0.0, val)

        val = meta_attrs_tree['p4']
        self.assertEqual(bool, type(val))
        self.assertEqual(True, val)

        val = meta_run_attrs_tree['p4']
        self.assertEqual(bool, type(val))
        self.assertEqual(True, val)

        val = meta_attrs_tree['p2']
        self.assertEqual(dict, type(val))
        self.assertEqual({'foo': 'bar'}, val)

        val = meta_run_attrs_tree['p2']
        self.assertEqual(dict, type(val))
        self.assertEqual({'foo': 'bar'}, val)

        val = meta_attrs_tree['p5']
        self.assertEqual(list, type(val))
        self.assertEqual(['x', 1, 2], val)

        val = meta_run_attrs_tree['p5']
        self.assertEqual(list, type(val))
        self.assertEqual(['x', 1, 2], val)

        val = meta_attrs_tree['p6']
        self.assertEqual(None, val)

        val = meta_run_attrs_tree['p6']
        self.assertEqual(None, val)

        val = meta_attrs_tree['p7']
        self.assertEqual(str, type(val))
        self.assertEqual('bazե\x00a-a', val)

        val = meta_run_attrs_tree['p7']
        self.assertEqual(str, type(val))
        self.assertEqual('bazե\x00a-a', val)

        val = meta_attrs_tree['p8']
        self.assertEqual(bytes, type(val))
        self.assertEqual(b'blob', val)

        val = meta_run_attrs_tree['p8']
        self.assertEqual(bytes, type(val))
        self.assertEqual(b'blob', val)
