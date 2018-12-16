import requests
import json
import re
import sys
from requests.auth import HTTPDigestAuth
import xml.etree.ElementTree as xml

lock_token = None

class HttpInterface:
    def __init__(self, data):
        self.data = data
        self.token_pattern = re.compile('^.*<D:locktoken><D:href>opaquelocktoken:([A-z\d-]*)<\/D:href>\n?<\/D:locktoken>')

        if self.data['base_url'][-1] == '/': self.data['base_url'] = self.data['base_url'][:-1]

    def lock(self, resource):
        _, data = self.__make_request('LOCK', resource, {'Accept': '*/*', 'Content-Type': 'application/xml'}, body=self.data['body'].replace('{username}', self.data['username']))
        data = data.replace('\n', '')

        try:
            return self.token_pattern.match(data).group(1)
        except:
            return ''

    def unlock(self, resource, lock_token):
        self.__make_request('UNLOCK', resource, {'Accept': '*/*', 'Lock-Token': '<opaquelocktoken:' + lock_token + '>'})
    
    def get(self, resource):
        return self.__make_request('GET', resource, {'Accept': '*/*'})

    def put(self, resource, content, lock_token):
        if resource.startswith('/'): resource = resource[1:]
        self.__make_request('PUT', resource, {'Accept': '*/*', 'If': '<' + self.data['base_url'] + '/' + resource  + '> (<opaquelocktoken:' + lock_token + '>)'}, body=content)
    
    def __make_request(self, method, resource, headers, body=None):
        if resource.startswith('/'): resource = resource[1:]
        response = requests.request(
            method=method,
            url=self.data['base_url'] + '/' + resource,
            auth=HTTPDigestAuth(self.data['username'], self.data['password']),
            headers=headers,
            data=body
        )
        return response.headers, response.content.decode('UTF-8')

class SyncManager:
    def __init__(self, data_path):
        self.etags = {}
        self.data = self.load_json(data_path)
        self.http = HttpInterface(self.data)

    def load_json(self, path):
        with open(path) as f:
            json_string = f.read()
            return json.loads(json_string)

    def sync_files(self):
        tokens = {res: self.http.lock(res) for res in self.data['resources'] + [self.data['main']]}

        get_results = [(res, self.http.get(res)) for res in self.data['resources'] if tokens[res]]

        self.etags = {res[0]: res[1][0]['ETag'] for res in get_results}
        files = {res[0]: res[1][1] for res in get_results}
        main = xml.fromstring(self.http.get(self.data['main'])[1])

        if not main: sys.exit(0)

        for res, content in files.items():
            name = res[res.find('/')+1:res.index('.')]
            name = name[0].upper() + name[1:]

            tasks = xml.fromstring(content).find('tasks').findall('task')
            subsection = main.find('tasks').find('task[@name="' + name + '"]')
            
            for child in list(subsection):
                subsection.remove(child)

            for t in tasks:
                subsection.append(t)
            print('Added tasks from ' + name.lower())

        self.http.put(self.data['main'], xml.tostring(main).decode('UTF-8'), tokens[self.data['main']])

        for res, token in tokens.items():
            if token: self.http.unlock(res, token)

    def files_have_changed(self):
        etags = {res: self.http.get(res)[0]['ETag'] for res in self.data['resources']}

        for k, v in etags.items():
            if not k in self.etags or self.etags[k] != v:
                return True

        return False