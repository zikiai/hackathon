"""Small synthetic regression checks; these are not accuracy evaluations."""
import base64
from io import BytesIO
import unittest
import pandas as pd
from server import analyse


def workbook():
    data = {'Time': pd.date_range('2026-01-01', periods=4, freq='min')}
    for number in range(1, 9):
        prefix = f'Car {number:02d} - '
        data[prefix+'Indoor Average Temperature'] = [20+number]*4
        data[prefix+'ACV Control Temperature (Cooling)'] = [20]*4
        data[prefix+'ACV Running Mode'] = ['Automatic Cooling']*4
        data[prefix+'ACV Information Valid'] = ['Valid']*4
    stream = BytesIO()
    pd.DataFrame(data).to_excel(stream, index=False)
    return base64.b64encode(stream.getvalue()).decode()


class AcvAdapterTests(unittest.TestCase):
    def test_ranking_evidence_and_exact_export(self):
        result = analyse({'files':[{'name':'case.xlsx','content':workbook()}]})
        self.assertEqual(result['csv'], 'file_id,ranked_cars\ncase.xlsx,08|07|06|05|04|03|02|01\n')
        case = result['cases'][0]
        self.assertEqual(case['ranking'][0]['car'], '08')
        self.assertEqual(case['ranking'][0]['average_positive_gap'], 8)
        self.assertEqual(case['charts']['07']['indoor'], [27]*4)
        self.assertEqual(len(case['times']), 4)

    def test_invalid_batches(self):
        item = {'name':'case.xlsx','content':workbook()}
        for files in [[], [item, item], [{'name':'../case.xlsx','content':item['content']}],
                      [{'name':'case.xlsx','content':'not base64!'}],
                      [item, {'name':'broken.xlsx','content':base64.b64encode(b'broken').decode()}]]:
            with self.subTest(files=len(files)), self.assertRaises(ValueError):
                analyse({'files':files})


if __name__ == '__main__':
    unittest.main()
