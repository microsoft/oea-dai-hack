import random


buffer = 'SIS ID,FederalRaceCategory,PrimaryLanguage,ELLStatus,SpecialEducation,LowIncome,City/Region\n'
for x in range(1,101):
    buffer += 'st' + str(x) + ','
    buffer += random.choices(['Asian', 'Black', 'Indian', 'White', 'American Indian'], weights=(25, 15, 35, 5, 20))[0] + ','
    buffer += random.choices(['English', 'Spanish', 'German', 'French', 'Japanese'], weights=(85, 10, 2, 2, 1))[0] + ','
    buffer += random.choices(['', 'English Learner', 'Initially Fluent English Proficient', 'Redesignated Fluent English Proficient'], weights=(80, 10, 5, 5))[0] + ','
    buffer += random.choices(['', 'Designated Instruction Service', 'Resource Specialty Program', 'Special Day Class'], weights=(80, 10, 5, 5))[0] + ','
    buffer += random.choices(['0', '1'], weights=(60, 40))[0] + ','
    buffer += random.choices(['Hyderabad', 'Chennai', 'Bangalore', 'Kochi', 'Vizag','Pondicherry','Mysore','Madurai','Ooty','Munnar'], weights=(25, 10, 25, 5, 10, 5, 5, 5, 5, 5))[0] + '\n'


print(buffer)
with open('mycsvfile.csv','w') as f:
    f.write(buffer)
