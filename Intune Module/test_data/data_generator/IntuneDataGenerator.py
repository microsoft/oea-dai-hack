from ctypes import windll
from faker import Faker
import csv
import random
import os
import shutil

DEVICE_DATA = [
    {
        'Make': 'Dell',
        'Model': ['Vostro 15 3501','Vostro 5410','Latitude 15 5520']
    },
    {
        'Make': 'Lenovo',
        'Model': ['ThinkBook 14s Yoga','Yoga Slim 7','X1 Titanium Yoga']
    },
    {
        'Make': 'HP',
        'Model': ['ENVY Laptop 14-eb0019TX','Pavilion Laptop 14-ec0007AX','Spectre x360 14-ea0542TU']
    }
]
OS_TYPES = ['Windows','Android','iOS/iPadOS','macOS']
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

class AzureIntuneDataGenerator:
    def __init__(self, number_of_records = 100):
        self.number_of_records = number_of_records
        self.faker = Faker('en_US')
        Faker.seed(1)

    def generate_data(self,writer):
        intune_data = []
        device = random.choice(DEVICE_DATA)

        for _ in range(100):
            intune_data.append({
                'DeviceId': self.faker.uuid4(),
                'Model': '{} {}'.format(device['Make'],random.choice(device['Model'])), 
                'LastContact': str(self.faker.date_time_between(start_date='-30d', end_date='now')),
                'UPN': self.faker.free_email(),
                'OS': random.choice(OS_TYPES)
            })
    
        writer.write(f'Intune/device.csv',self.list_of_dict_to_csv(intune_data))

    def list_of_dict_to_csv(self,list_of_dict, includeHeaders = True):
        csv_str = ''
        if includeHeaders == True:
            header = []
            for column_name in list_of_dict[0].keys(): 
                if not column_name.startswith('_'): header.append(column_name)
            csv_str += ",".join(header) + "\n"
        #print(list_of_dict)
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

dg = AzureIntuneDataGenerator()
writer = FileWriter(destination)
dg.generate_data(writer)


