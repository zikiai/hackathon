import unittest
from build_submission import validate, EXPECTED

class SchemaTests(unittest.TestCase):
    def test_rail_complete(self):
        text='file_id,prediction\n'+''.join(f'{name},Normal\n' for name in EXPECTED['rail'])
        self.assertEqual(len(validate('rail',text)),68)
        with self.assertRaises(AssertionError):validate('rail','file_id,prediction\nTest1.csv,Normal\n')
        with self.assertRaises(AssertionError):validate('rail',text.replace('Normal','normal'))
    def test_door_native_timestamps(self):
        text='start_time,end_time,prediction\n2023-7-5-0-1-2-40,2023-7-5-0-1-4-840,Normal\n'
        self.assertEqual(len(validate('door',text)),1)
        with self.assertRaises(AssertionError):validate('door',text.replace('start_time,end_time','file_id,end_time'))
    def test_acv_exact_ids(self):
        text='file_id,ranked_cars\nacv_test_case.xlsx,01|03|07|04|08|06|02|05\n'
        self.assertEqual(len(validate('acv',text)),1)
        with self.assertRaises(AssertionError):validate('acv',text.replace('01|','1|'))
    def test_shm_finite(self):
        text='file_id,prediction\n'+''.join(f'{name},0.1\n' for name in EXPECTED['shm'])
        self.assertEqual(len(validate('shm',text)),16)
        with self.assertRaises(AssertionError):validate('shm',text.replace('0.1','nan'))

if __name__=='__main__':unittest.main()
