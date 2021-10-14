import json
from faker import Faker
import random
import os
import shutil

MODELS = ['null', 'Surface Go', 'TravelMate B311-31', 'OEMST Product Name DV', 'HP Stream 11 Pro G5', 'Virtual Machine', 'VivoBook_ASUS Laptop E410MA_L410MA', 'HP Stream Laptop 11-ak0xxx','Surface Pro 6']
OPERATING_SYSTEM = ['Windows', 'macOS', 'AndroidForWork', 'iOS/iPadOS', 'Windows Mobile', 'IPhone']

_path = os.path.dirname(__file__)
Users_file = open("Users.json")
Users = json.load(Users_file)

AzureAdIDs = []
Result = []
Final = {}

for values in Users:
    for data in values['value']:
        AzureAdIDs.append(data['id'])

class FileWriter:
    def __init__(self, root_destination=None):
        if not root_destination: self.root_destination = ''
        elif not root_destination.endswith('/'): self.root_destination = root_destination + '/'
        else: self.root_destination = root_destination
        self.writers = {}

    def write(self, path_and_filename, data_str):
        path_and_filename = self.root_destination + path_and_filename
        if path_and_filename not in self.writers.keys():
            if not os.path.exists(os.path.dirname(path_and_filename)):
                os.makedirs(os.path.dirname(path_and_filename))
            self.writers[path_and_filename] = open(path_and_filename, 'a')
        
        self.writers[path_and_filename].write(data_str) 

class AzureAdDataGenerator:
    def __init__(self):
        self.faker = Faker('en-US')
        Faker.seed(1)

    def generate_data(self,writer):
        for Id in AzureAdIDs:
            Result.append({
                "id": Id,
                "deviceId": self.faker.uuid4().replace('-',''),
                "model": random.choice(MODELS),
                "operatingSystem":random.choice(OPERATING_SYSTEM)
            })
        writer.write(f'AzureAD/devicesInfo.csv', self.list_of_dict_to_csv(Result))

    def list_of_dict_to_csv(self,list_of_dict, includeHeaders = True):
        csv_str = ''
        if includeHeaders == True:
            header = []
            for column_name in list_of_dict[0].keys(): 
                if not column_name.startswith('_'): header.append(column_name)
            csv_str += ",".join(header) + "\n"

        for row in list_of_dict:
            csv_str += self.obj_to_csv(row) + "\n"

        return csv_str

    def obj_to_csv(self,obj):
        csv = ''
        for key in obj:
            if not (key.startswith('_')): csv += str(obj[key]) + ','
        return csv[:-1]




destination = 'tmp_generated_data'
if os.path.exists(destination): shutil.rmtree(destination)
os.makedirs(destination)

dg = AzureAdDataGenerator()
writer = FileWriter(destination)
dg.generate_data(writer)
