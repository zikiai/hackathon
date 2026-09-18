import io
import unittest
from unittest.mock import patch
from cloud_server import app, LOCAL

class CloudTests(unittest.TestCase):
    def setUp(self):
        self.client=app.test_client(); LOCAL.clear()
    def test_health_and_private_files(self):
        self.assertEqual(self.client.get('/api/health').status_code,200)
        for url in ['/cloud_server.py','/pipelines.py','/.env','/../Dockerfile']:
            self.assertEqual(self.client.get(url).status_code,404)
    @patch('cloud_server.analyse_file',return_value={'records':[],'csv':'file_id,prediction\n'})
    def test_saved_result_is_visitor_scoped(self,_):
        response=self.client.post('/api/analyse/rail',data={'file':(io.BytesIO(b'x'),'Test.csv')})
        self.assertEqual(response.status_code,200,response.json)
        url='/api/results/'+response.json['analysis_id']
        self.assertEqual(self.client.get(url).status_code,200)
        self.assertEqual(app.test_client().get(url).status_code,404)
    def test_bad_inputs(self):
        self.assertEqual(self.client.post('/api/analyse/rail',headers={'Origin':'https://evil.example'},data={}).status_code,403)
        for name in ['../bad.csv','bad.exe','bad\n.csv']:
            self.assertEqual(self.client.post('/api/analyse/rail',data={'file':(io.BytesIO(b'x'),name)}).status_code,400)
        self.assertEqual(self.client.post('/api/analyse/acv',data={'file':(io.BytesIO(b'broken'),'bad.xlsx')}).status_code,400)

if __name__=='__main__':unittest.main()
