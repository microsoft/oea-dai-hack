import csv
import os
import shutil
import random
import math
from faker import Faker

SUBJECTS = ['Math - Algebra', 'Math - Geometry', 'English Language', 'History - World History',
            'Science Biology', 'Health', 'Technology - Programming', 'Physical Education', 'Art', 'Music']
SCHOOL_TYPES = ['High', 'High', 'High']


class MSInsightsDataGenerator:
    """ This is a starting point for the data generator for the new MS Insights roster and activity format.
        todo: Note that a fair amount of work is left for this to generate data that aligns with the new roster 
        format as defined in the roster.v0.3.2.cdm.json spec, and the activity format as defined in activity.v0.1.0.cdm.json
    """
    def __init__(self, activity_min_per_person=5, activity_max_per_person=20, students_per_school=100, classes_in_student_schedule=6, students_per_section=25, student_teacher_ratio=9, include_optional_fields=True,
                 fall_semester_start_date='2021-08-15', fall_semester_end_date='2021-12-15', spring_semester_start_date='2022-01-10', spring_semester_end_date='2022-05-10'):
        # Set a seed value in Faker so it generates the same values every time it's run
        self.faker = Faker('en_US')
        Faker.seed(1)

        self.activity_min_per_person = activity_min_per_person
        self.activity_max_per_person = activity_max_per_person
        self.students_per_school = students_per_school
        self.classes_in_student_schedule = classes_in_student_schedule
        self.students_per_section = students_per_section
        self.student_teacher_ratio = student_teacher_ratio
        self.include_optional = include_optional_fields
        self.fall_semester_start_date = fall_semester_start_date
        self.fall_semester_end_date = fall_semester_end_date
        self.spring_semester_start_date = spring_semester_start_date
        self.spring_semester_end_date = spring_semester_end_date
        self.school_year = '2021'

        self.teachers_per_school = math.ceil(self.students_per_school/self.student_teacher_ratio)
        self.section_id = 1
        self.student_id = 1
        self.teacher_id = 1
        self.course_id = 1
        self.school_id = 1
        self.term_id = 1
        self.domain = '@Classrmtest86.org'

    def generate_data(self, num_of_schools, writer):
        schools = ''

        for n in range(num_of_schools):
            school_data = self.create_school(n)
            m365_data = self.format_m365_data(school_data)
            schools += m365_data.pop('Org')
            for key in m365_data.keys(): 
                writer.write(f"M365/roster/2021-07-12/{key}/part-00000-71379e08-1ce0-425f-9447-775b0dc134f1-example.csv", m365_data[key])
            # Create empty files to reflect the empty files we currently get from MS Insights
            empty_files_to_create = ['AadGroup', 'AadGroupMembership', 'AadUserPersonMapping', 'CourseGradeLevel', 'CourseSubject', ]
            for entity in empty_files_to_create:
                path_and_filename = f"M365/roster/2021-07-12/{entity}/part-00000-71379e08-1ce0-425f-9447-775b0dc134f1-example.csv"
                writer.write(path_and_filename, '')



            writer.write('contoso_sis/attendance.csv', school_data.pop('_attendance'))
            writer.write('contoso_sis/section_marks.csv', school_data.pop('_section_marks'))
            writer.write('contoso_sis/students.csv', self.list_of_dict_to_csv(school_data['_students']))

            self.create_and_write_activity_data(school_data['_students'], 'M365/activity/2021-07-12/ApplicationUsage.Part001.csv', writer)
            self.create_and_write_activity_data(school_data['_teachers'], 'M365/activity/2021-07-12/ApplicationUsage.Part002.csv', writer)

        writer.write('m365/Org.csv', schools)

    def create_school(self, school_id):
        school_id = 'sch' + str(school_id)
        fname = self.faker.first_name()
        lname = self.faker.last_name()
        school = {
            'SIS ID': school_id,
            'Name': self.get_fake_school_name(),
            'School Number': school_id if self.include_optional else '',
            'School NCES_ID': school_id if self.include_optional else '',
            'Grade Low': '9' if self.include_optional else '',
            'Grade High': '12' if self.include_optional else '',
            'State ID': school_id if self.include_optional else '',
            'Principal SIS ID': '02100' if self.include_optional else '',
            'Principal Name': f"{fname} {lname}" if self.include_optional else '',
            'Principal Secondary Email': f"{fname.lower()}.{lname.lower()}{self.domain}" if self.include_optional else '',
            'Address': self.faker.building_number() if self.include_optional else '',
            'City': self.faker.city() if self.include_optional else '',
            'State': 'WA' if self.include_optional else '',
            'Zip': '98074' if self.include_optional else '',
            'Country': 'US' if self.include_optional else '',
            'Phone': self.faker.phone_number() if self.include_optional else '',
            'Zone': '1' if self.include_optional else '',
        }

        school['_calendar'] = {'Id': f'edp_cal{school_id}',
                            'Name': f'{self.school_year} Calendar',
                            'Description': f'calendar for {self.school_year}',
                            'SchoolYear': self.school_year,
                            'IsCurrent': 'True',
                            'ExternalId': f'cal{school_id}',
                            'CreateDate': '8/13/2020 10:36:44 AM',
                            'LastModifiedDate': '8/15/2020 11:36:00 PM',
                            'IsActive': 'True',
                            'OrgId': f'edp_{school_id}'
                            }
        school['_students'] = self.create_students(school['SIS ID'])
        school['_teachers'] = self.create_teachers(school['SIS ID'])
        school['_courses'] = self.create_courses(school['_calendar']['Id'])
        school['_terms'] = self.create_terms(school['_calendar']['Id'])
        for term in school['_terms']:
            self.create_sections(term, school['SIS ID'], school['_courses'])

        self.add_student_data(school) # adds student_section_membership, attendance, section_marks
        self.add_teacher_data(school) # staff_section_membership

        return school

    def format_m365_data(self, school):
        ref_aad_id = '7DAF8820-6691-4D61-A210-CE94EA7D3667'
        ref_upn_id = '450E6525-61A6-4BF6-A3D5-F95EB5CB1183'
        parent_org_id = 'sch0'
        ref_org_type_district = '1198ADF7-3DA7-4DA6-A8CB-6FC3313C063C'
        ref_org_type_school = '0AA7E195-1576-440B-817C-BCCA6949E2ED'
        ref_student_org_role = '0D16FCED-6DC7-4235-90BF-724D40ABC7BD'
        ref_staff_org_role = '03FFC8C5-9C64-4321-8041-334F07A252F0'
        ref_enrollment_status = 'F36F047A-F410-4761-B41F-17B952A8EAD4'
        ref_section_type = '96669810-AB33-4B0F-92BE-6E2CC6F30EE9'
        ref_session_type = '1C69DBD1-5CDA-44B2-AEAA-510F9D5DA98D'
        source_system_id = 'edp_SIS1'
        datetime_str = "8/13/2020 10:09:43 AM"        

        m365_data = {}
        m365_data['RefDefinition'] = REF_DEFINITION_CSV
        #m365_data['Calendar'] = self.obj_to_csv(school['_calendar']) + "\n"
        m365_data['Org'] = f"edp_{school['SIS ID']},{school['Name']},{school['School Number']},{school['SIS ID']},{datetime_str},{datetime_str},True,edp_{parent_org_id},{ref_org_type_school},{source_system_id}\n"
        m365_data['StudentSectionMembership'] = school['_student_section_membership']
        m365_data['StaffSectionMembership'] = school['_staff_section_membership']

        m365_data['Person'] = ''
        m365_data['StudentOrgAffiliation'] = ''
        m365_data['StaffOrgAffiliation'] = ''
        m365_data['PersonIdentifier'] = ''
        m365_data['Section'] = ''
        m365_data['Session'] = ''
        m365_data['Course'] = ''

        for student in school['_students']:
            m365_data['StudentOrgAffiliation'] += f"edp_oa_{student['SIS ID']},True,,,oa_{student['SIS ID']},{datetime_str},{datetime_str},True,edp_{school['SIS ID']},edp_{student['SIS ID']},{self.get_grade_ref(student['Grade'])},{ref_student_org_role},{ref_enrollment_status}\n"
            m365_data['Person'] += f"edp_{student['SIS ID']},{student['First Name']},{student['Middle Name']},{student['Last Name']},,,True,{student['SIS ID']},{datetime_str},{datetime_str},True,{source_system_id}\n"
            m365_data['PersonIdentifier'] += f"edp_pi1_{student['SIS ID']},{student['_upn']},,{ref_upn_id},pi1_{student['SIS ID']},{datetime_str},{datetime_str},True,edp_{student['SIS ID']},{source_system_id}\n"
            m365_data['PersonIdentifier'] += f"edp_pi2_{student['SIS ID']},{student['_aad']},,{ref_aad_id},pi2_{student['SIS ID']},{datetime_str},{datetime_str},True,edp_{student['SIS ID']},{source_system_id}\n"
        for teacher in school['_teachers']:
            m365_data['StaffOrgAffiliation'] += f"edp_oa_{teacher['SIS ID']},True,,,oa_{teacher['SIS ID']},{datetime_str},{datetime_str},True,edp_{school['SIS ID']},edp_{teacher['SIS ID']},,{ref_staff_org_role}\n"
            m365_data['Person'] += f"edp_{teacher['SIS ID']},{teacher['First Name']},{teacher['Middle Name']},{teacher['Last Name']},,,True,{teacher['SIS ID']},{datetime_str},{datetime_str},True,{source_system_id}\n"
            m365_data['PersonIdentifier'] += f"edp_pi1_{teacher['SIS ID']},{teacher['_upn']},,{ref_upn_id},pi1_{teacher['SIS ID']},{datetime_str},{datetime_str},True,edp_{teacher['SIS ID']},{source_system_id}\n"
            m365_data['PersonIdentifier'] += f"edp_pi2_{teacher['SIS ID']},{teacher['_aad']},,{ref_aad_id},pi2_{teacher['SIS ID']},{datetime_str},{datetime_str},True,edp_{teacher['SIS ID']},{source_system_id}\n"
        for term in school['_terms']:
        # todo: need to convert the term startdate and enddate to be the format that is expected to be coming from EDP (rather than the format used for sds)
            m365_data['Session'] += f"edp_{term['Term SIS ID']},{term['Term Name']},{term['Term StartDate']},{term['Term EndDate']},{term['Term SIS ID']},8/13/2020 10:36:44 AM,8/15/2020 11:36:00 PM,True,{term['_calendar_id']},,{ref_session_type}\n"
        for section in term['_sections']:
            m365_data['Section'] += f"edp_{section['SIS ID']},{section['Section Name']},{section['Section Number']},,{section['SIS ID']},{datetime_str},{datetime_str},True,edp_{section['Course SIS ID']},{ref_section_type},edp_{section['Term SIS ID']},edp_{section['School SIS ID']}\n"
        for course in school['_courses']:
        # columns for DIP csv are: Id,Name,Code,Description,ExternalId,CreateDate,LastModifiedDate,IsActive,CalendarId
            m365_data['Course'] += f"edp_{course['Course SIS ID']},{course['Course Name']},{course['Course Number']},{course['Course Description']},{course['Course SIS ID']},8/13/2020 10:36:44 AM,8/15/2020 11:36:00 PM,True,{course['_calendar_id']}\n"

        return m365_data

    def create_terms(self, calendar_id):
        terms = []
        terms.append({
            'Term SIS ID': 'term' + str(self.term_id),
            'Term Name': 'Fall Semester',
            'Term StartDate': '9/1/2019',
            'Term EndDate': '12/22/2019',
            '_sections': [],
            # this is an array of arrays representing the sections and the spots (available seats) within each section
            '_section_spots': [],
            '_calendar_id': calendar_id
        })
        self.term_id += 1
        terms.append({
            'Term SIS ID': 'term' + str(self.term_id),
            'Term Name': 'Spring Semester',
            'Term StartDate': '1/21/2020',
            'Term EndDate': '5/30/2020',
            '_sections': [],
            '_section_spots': [],
            '_calendar_id': calendar_id
        })
        self.term_id += 1
        return terms

    def create_courses(self, calendar_id):
        courses = []
        for subject in SUBJECTS:
            courses.append({
                'Course SIS ID': 'course' + str(self.course_id),
                'Course Name': subject,
                'Course Number': str(self.course_id),
                'Course Description': "Instruction covering " + subject,
                'Course Subject': subject,
                '_calendar_id': calendar_id
            })
            self.course_id += 1
        return courses

    def create_students(self, school_id):
        students = []
        gender = random.choice(['Male', 'Female'])
        if gender == 'Male': fname = self.faker.first_name_male()
        else: fname = self.faker.first_name_female()

        for n in range(self.students_per_school):
            fname = self.faker.first_name()
            lname = self.faker.last_name()
            email = f"{fname.lower()}{lname.lower()}{self.student_id}{self.domain}"
            students.append({
                'SIS ID': 'st' + str(self.student_id),
                'School SIS ID': school_id,
                'Username': f"{fname.lower()}{lname.lower()}{self.student_id}",
                'Password': self.faker.password() if self.include_optional else '',
                'First Name': fname,
                'Last Name': lname,
                'Middle Name': self.faker.first_name() if self.include_optional else '',
                'Secondary Email': email if self.include_optional else '',
                'Student Number': str(self.student_id) if self.include_optional else '',
                'Grade': random.choice(['9', '10', '11', '12']) if self.include_optional else '',
                'State ID': '123' if self.include_optional else '',
                'Status': 'Active' if self.include_optional else '',
                'Birthdate': '4/2/2004' if self.include_optional else '',
                'Graduation Year': '2020' if self.include_optional else '',
                'Gender': gender,
                'FederalRaceCategory': random.choice(['Asian', 'Black', 'White', 'Hispanic', 'American Indian']),
                'PrimaryLanguage': random.choices(['English', 'Spanish', 'German', 'French', 'Japanese'], weights=(85, 10, 2, 2, 1))[0],
                'ELLStatus': random.choices(['', 'English Learner', 'Initially Fluent English Proficient', 'Redesignated Fluent English Proficient'], weights=(80, 10, 5, 5))[0],
                'SpecialEducation': random.choices(['', 'Designated Instruction Service', 'Resource Specialty Program', 'Special Day Class'], weights=(80, 10, 5, 5))[0],
                'LowIncome': random.choices([0, 1], weights=(60, 40))[0],
                'CumulativeGPA': random.choice([0.523, 0.423, 1.13, 2.63, 2.33, 3.33, 4.0]),                
                '_role': 'Student',
                '_section_ids': [],
                '_upn': email,
                '_aad': self.faker.uuid4()
            })
            self.student_id += 1
        return students

    def create_teachers(self, school_id):
        teachers = []
        for n in range(self.teachers_per_school):
            fname = self.faker.first_name()
            lname = self.faker.last_name()
            email = f"{fname.lower()}{lname.lower()}{self.teacher_id}{self.domain}"
            teachers.append({
                'SIS ID': 't' + str(self.teacher_id),
                'School SIS ID': school_id,
                'Username': f"{fname.lower()}{lname.lower()}{self.teacher_id}",
                'Password': self.faker.password() if self.include_optional else '',
                'First Name': fname,
                'Last Name': lname,
                'Middle Name': self.faker.first_name() if self.include_optional else '',
                'Secondary Email': email if self.include_optional else '',
                'Teacher Number': str(self.teacher_id) if self.include_optional else '',
                'State ID': '123' if self.include_optional else '',
                'Status': 'Active' if self.include_optional else '',
                'Title': 'Teacher' if self.include_optional else '',
                'Qualification': 'EdLD' if self.include_optional else '',
                '_role': 'Teacher',
                '_section_ids': [],
                '_upn': email,
                '_aad': self.faker.uuid4()
            })
            self.teacher_id += 1
        return teachers

    def create_sections(self, term, school_id, courses):
        spots_needed = self.students_per_school * self.classes_in_student_schedule
        # determine the number of sections needed
        sections_needed = math.ceil(spots_needed / self.students_per_section) + 1
        for n in range(sections_needed):
            course = random.choice(courses)
            term['_sections'].append({
                'SIS ID': 'sec' + str(self.section_id),
                'School SIS ID': school_id,
                'Section Name': course['Course Subject'] + " " + str(self.section_id),
                'Section Number': str(self.section_id) if self.include_optional else '',
                'Term SIS ID': term['Term SIS ID'] if self.include_optional else '',
                'Term Name': term['Term Name'] if self.include_optional else '',
                'Term StartDate': term['Term StartDate'] if self.include_optional else '',
                'Term EndDate': term['Term EndDate'] if self.include_optional else '',
                'Course SIS ID': course['Course SIS ID'] if self.include_optional else '',
                'Course Name': course['Course Name'] if self.include_optional else '',
                'Course Number': course['Course Number'] if self.include_optional else '',
                'Course Description': course['Course Description'] if self.include_optional else '',
                'Course Subject': course['Course Subject'] if self.include_optional else '',
                'Periods': '2' if self.include_optional else '',
                'Status': 'Active' if self.include_optional else ''
            })
            # add section spots
            spots = []
            for i in range(self.students_per_section):
                spots.append('sec' + str(self.section_id))
            term['_section_spots'].append(spots)
            self.section_id += 1

    def get_grade_ref(self, grade_str):
        if grade_str == '9': return '4429F333-536A-458F-AE87-FDF5471B5E8D'
        elif grade_str == '10': return 'B6747F48-667B-4F0D-8438-9D1B180A3791'
        elif grade_str == '11': return '490702EA-9AC0-435E-AB8F-C1999BB0B393'
        else: return '37DB651A-E2CC-4C16-8F52-27D4FA17B680'

    def add_student_data(self, school):
        ref_student_section_role = 'D1CA502E-DB62-41D2-B438-AC669E6A9663'
        datetime_str = "8/13/2020 10:09:43 AM"
        mark_id = 1
        school['_student_section_membership'] = ''
        school['_attendance'] = ''
        school['_section_marks'] = ''

        for student in school['_students']:
            for term in school['_terms']:
                num_enrollments = 0
                for section_spots in term['_section_spots']:
                    if(len(section_spots) == 0): 
                        continue
                    else:
                        spot_taken = section_spots.pop()
                        student['_section_ids'].append(spot_taken)
                        school['_student_section_membership'] += f"edp_ssm_{student['SIS ID']},,,ssm_{student['SIS ID']},{datetime_str},{datetime_str},True,edp_{student['SIS ID']},,{ref_student_section_role},edp_{spot_taken}\n"
                        num_enrollments += 1
                        school['_attendance'] += f"att_{student['SIS ID']},{student['SIS ID']},{self.school_year},{school['SIS ID']},8/15/2020,No,1,{spot_taken},P,1,Present,ClassSectionAttendance,0\n"
                        grade = self.get_random_grade()
                        credits_earned = 5
                        if grade[1] == 'F': credits_earned = 0
                        school['_section_marks'] += f"m{mark_id},{student['SIS ID']},{spot_taken},,{term['Term SIS ID']},{grade[0]},{grade[1]},No,5,{credits_earned},\n"
                        mark_id += 1
                    if (num_enrollments >= self.classes_in_student_schedule): break        

    def add_teacher_data(self, school):
        ref_staff_section_role = 'C943E793-2DB7-47C0-B187-A9ED65EEBD5B'
        datetime_str = "8/13/2020 10:09:43 AM"
        school['_staff_section_membership'] = ''
        for term in school['_terms']:
            teacher_index = 0
            for section in term['_sections']:
                teacher = school['_teachers'][teacher_index]
                teacher['_section_ids'].append(section['SIS ID'])
                school['_staff_section_membership'] += f"edp_ssm_{teacher['SIS ID']},True,,,ssm_{teacher['SIS ID']},{datetime_str},{datetime_str},True,edp_{teacher['SIS ID']},{ref_staff_section_role},edp_{section['SIS ID']}\n"
                teacher_index += 1
                if (teacher_index == len(school['_teachers'])):
                    teacher_index = 0  # start over from the beginning of the list of teachers

    def create_and_write_activity_data(self, people, path_and_filename, writer):
        signal_id_counter = 100
        signal_types = ['VisitTeamChannel', 'ReactedWithEmoji', 'PostChannelMessage', 'ReplyChannelMessage', 'ExpandChannelMessage', 'CallRecordSummarized', 'FileAccessed', 'FileDownloaded',
                        'FileModified', 'FileUploaded', 'ShareNotificationRequested', 'CommentCreated', 'UserAtMentioned', 'AddedToSharedWithMe', 'CommentDeleted', 'Unlike']
        agents = ['', '"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.182 Safari/537.36 Edg/88.0.705.74"', '"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Teams/1.3.00.34662 Chrome/80.0.3987.165 Electron/8.5.1 Safari/537.36"',
                '"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36"', '"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:78.0) Gecko/20100101 Firefox/78.0"']
        applications = ['Other apps', 'Teams', 'PowerPoint', 'Excel', 'PDF viewers', 'Media apps', 'Image apps', 'Word']
        learning_activities = ['Communications', 'Assignments', 'Meetings']

        # activity_csv.write('SignalType,StartTime,UserAgent,SignalId,SISClassId,OfficeClassId,ChannelId,AppName,ActorId,ActorRole,SchemaVersion,AssignmentId,SubmissionId,Action,AssginmentDueDate,ClassCreationDate,Grade,SourceFileExtension,MeetingDuration')
        num_of_entries_for_person = self.faker.pyint(min_value=self.activity_min_per_person, max_value=self.activity_max_per_person)
        for i in range(num_of_entries_for_person):
            for person in people:
                signal_type = random.choice(signal_types)
                start_time = f"{self.faker.date_time_between(start_date='-60d', end_date='now', tzinfo=None)}.0000000"
                agent = random.choice(agents)
                signal_id = self.faker.uuid4()
                sis_class_id = random.choice(person['_section_ids'])
                office_class_id = f"office_id_{sis_class_id}"
                if signal_type == 'CallRecordSummarized':
                    channel_id = f"channel_{office_class_id}"
                else:
                    channel_id = ''
                app_name = random.choice(applications)
                actor_id = person['_aad']
                actor_role = person['_role']
                schema_version = '1.06'
                assignmentId = ''
                submissionId = ''
                action = ''
                assginment_due_date = ''
                class_creation_date = ''
                grade = ''
                source_file_extension = ''

                hours = self.faker.pyint(min_value=0, max_value=23)
                minutes = self.faker.pyint(min_value=0, max_value=59)
                meeting_duration = f'00:{hours:02}:{minutes:02}'

                # SignalType,StartTime,UserAgent,SignalId,SISClassId,OfficeClassId,ChannelId,AppName,ActorId,ActorRole,SchemaVersion,AssignmentId,SubmissionId,Action,AssginmentDueDate,ClassCreationDate,Grade,SourceFileExtension,MeetingDuration
                writer.write(path_and_filename, f"{signal_type},{start_time},{agent},{signal_id},{sis_class_id},{office_class_id},{channel_id},{app_name},{actor_id},{actor_role},{schema_version},{assignmentId},{submissionId},{action},{assginment_due_date},{class_creation_date},{grade},{source_file_extension},{meeting_duration}\n")

    def get_fake_school_name(self):
        name = self.faker.last_name()
        if name == 'Ho': return self.get_fake_school_name()
        else: return f"{name} {random.choice(SCHOOL_TYPES)}"

    def get_random_grade(self):
        num = random.randint(55, 110)
        grade = ''
        if num < 60: grade = 'F'
        elif num >= 60 and num < 70: grade = 'D'
        elif num >= 70 and num < 80: grade = 'C'
        elif num >= 80 and num < 90: grade = 'B'
        elif num >= 90: grade = 'A'
        return [str(num), grade]

    def list_of_dict_to_csv(self, list_of_dict):
        csv_str = ''
        header = []
        for column_name in list_of_dict[0].keys(): 
            if not column_name.startswith('_'): header.append(column_name)
        csv_str += ",".join(header) + "\n"

        for row in list_of_dict:
            csv_str += self.obj_to_csv(row) + "\n"

        return csv_str[:-1] # chop the final newline char

    def obj_to_csv(self, obj):
        csv = ''
        for key in obj:
            if not (key.startswith('_')): csv += str(obj[key]) + ','
        return csv[:-1]        

REF_DEFINITION_CSV="""
    F27548AC-5978-4DC7-8897-1F51FBBD269F,RefPhoneNumberType,ceds.ed.gov,Home,10,Home,True
    1C20AA37-0D47-428A-9886-275D9314683B,RefPhoneNumberType,ceds.ed.gov,Work,20,Work,True
    27127BF9-D27F-4550-8DB5-F5C45B9F300A,RefPhoneNumberType,ceds.ed.gov,Mobile,30,Mobile,True
    2058208C-D839-4050-811E-5C967ED3479A,RefPhoneNumberType,ceds.ed.gov,Fax,40,Fax,True
    F72DB3A7-60D1-4205-BCCE-261A5C70392A,RefPhoneNumberType,ceds.ed.gov,SMS,50,SMS (text),True
    BAB42A97-EF46-4D19-BD7C-A16042D69290,RefPhoneNumberType,ceds.ed.gov,Other,60,Other,True
    296C8859-65B6-41AF-9AC3-A756F805AA7A,RefEmailAddressType,ceds.ed.gov,Home,10,Home/personal,True
    2BD5CAF9-B2E2-4BB9-9634-D7F9D9C99942,RefEmailAddressType,ceds.ed.gov,Work,20,Work,True
    B62C5FF6-9C7C-4282-99DA-D989E975FED9,RefEmailAddressType,ceds.ed.gov,Organizational,30,Organizational,True
    BE4EDAD4-273B-4AC0-B0A9-4AEAAA4D72FC,RefEmailAddressType,ceds.ed.gov,Other,40,Other,True
    C7BA7784-18EA-48F7-A8CE-8F85317DB1FC,RefSessionType,imsglobal.org,gradingPeriod,10,Grading Period,True
    1C69DBD1-5CDA-44B2-AEAA-510F9D5DA98D,RefSessionType,imsglobal.org,semester,20,Semester,True
    535E0286-C64B-4E96-8866-8F05F7FD4B7D,RefSessionType,imsglobal.org,schoolYear,30,School Year,True
    D3244521-1657-44CC-878D-A731819A8C10,RefSessionType,imsglobal.org,term,40,Term,True
    9FC6B036-76CB-49C1-9B54-52B6DEA89B13,RefSessionType,imsglobal.org,quarter,50,Quarter,True
    9CFF5B20-9F10-40CD-BE70-337E1D45EC22,RefOrgType,imsglobal.org,department,10,Department,True
    0AA7E195-1576-440B-817C-BCCA6949E2ED,RefOrgType,imsglobal.org,school,20,School,True
    1198ADF7-3DA7-4DA6-A8CB-6FC3313C063C,RefOrgType,imsglobal.org,district,30,District,True
    DD0FD78C-8E83-4561-BCA9-D622C17239B1,RefOrgType,imsglobal.org,local,40,Local,True
    92FBF859-EAF5-44DB-A009-F078DC5D9624,RefOrgType,imsglobal.org,state,50,State,True
    CB89C3EF-00C6-4887-86F6-025E85EE0CD5,RefOrgType,imsglobal.org,national,60,National,True
    0D70E313-D121-4BEB-873E-32AB1BE585BB,RefOrgType,microsoft.com,departmentOfEducation,70,Department of Education,True
    A876151F-8E7B-4E0D-AD5E-1644489C06E2,RefOrgType,microsoft.com,ministryOfEducation,80,Ministry of Education,True
    4EF75D0A-C056-4708-BBA8-93974487E3FB,RefOrgType,microsoft.com,university,90,University,True
    A330F267-036A-49FD-9E41-BD04E33F72B4,RefOrgType,microsoft.com,college,100,College,True
    9E5B404E-F884-4213-BB5A-C13896B3C64F,RefOrgType,microsoft.com,campus,110,Campus,True
    E4DC78EC-B83E-490E-B2AC-A4002F2A1011,RefOrgType,microsoft.com,adultEducation,120,Adult Education,True
    3F7E3E4A-17D8-4528-8023-4C51E1135DAF,RefAcademicSubject,ceds.ed.gov,13371,10,Arts,False
    A8B9FD82-A3FE-4B58-B965-6D2485CAF4FF,RefAcademicSubject,ceds.ed.gov,73065,20,Career and Technical Education,False
    75C20E7F-4064-4E66-93D1-AD60D8AF03E3,RefAcademicSubject,ceds.ed.gov,13372,30,English,False
    B28AA87C-9357-40F3-8F3F-468D76100470,RefAcademicSubject,ceds.ed.gov,256,40,English as a second language (ESL),False
    11F6E7A0-188D-4F29-9A85-D6C64DEBF51A,RefAcademicSubject,ceds.ed.gov,546,50,Foreign Languages,False
    785C7805-478C-437E-9D0F-A42085F19CA6,RefAcademicSubject,ceds.ed.gov,73088,60,History Government - US,False
    67B144F0-B0B7-4B48-B948-A1C0C41C2316,RefAcademicSubject,ceds.ed.gov,73089,70,History Government - World,False
    8C053948-3868-4172-8439-90F3C763C1FB,RefAcademicSubject,ceds.ed.gov,554,80,Language arts,False
    406A9BDB-D00A-47B2-9B58-0D7C6BA4B5F3,RefAcademicSubject,ceds.ed.gov,1166,90,Mathematics,False
    6542AAA2-4241-41FA-8003-FE0D55C8C9B5,RefAcademicSubject,ceds.ed.gov,560,100,Reading,False
    EFE570C8-4863-41B1-8F7A-6FE6F17C3FF9,RefAcademicSubject,ceds.ed.gov,13373,110,Reading/Language Arts,False
    C78DB896-4E57-4118-93B0-4FBC0CFB4892,RefAcademicSubject,ceds.ed.gov,562,120,Science,False
    C105C6B3-3CF9-472F-B865-043979160403,RefAcademicSubject,ceds.ed.gov,73086,130,Science - Life,False
    8270A5B4-961D-49BC-93FF-B11B9A355800,RefAcademicSubject,ceds.ed.gov,73087,140,Science - Physical,False
    857C8075-F125-4316-9C7D-C6F06A59A3B4,RefAcademicSubject,ceds.ed.gov,13374,150,"Social Sciences (History, Geography, Economics, Civics and Government)",False
    71C56B0D-AD9A-44A9-83BD-B1346BA735FD,RefAcademicSubject,ceds.ed.gov,2043,160,Special education,False
    D998AFA4-15B2-454E-AD56-9BD67562DE09,RefAcademicSubject,ceds.ed.gov,1287,170,Writing,False
    125AD8F4-CBC2-4780-8ECA-766F6BB3616F,RefAcademicSubject,ceds.ed.gov,9999,180,Other,False
    AF074314-C807-431D-849E-5C56DCFD56FB,RefSex,ceds.ed.gov,Male,10,Male,True
    7BA57431-93E6-4F3A-B74F-56C84749E9A7,RefSex,ceds.ed.gov,Female,20,Female,True
    FEA3A014-218A-470A-AB59-12F3064DC397,RefSex,ceds.ed.gov,Not selected,30,Not selected,True
    C855A445-E7CC-4093-B6E3-E4B887C6FD92,RefState,ceds.ed.gov,AK,10,Alaska,True
    16B07D3F-571C-40E6-92AA-73178BEF1542,RefState,ceds.ed.gov,AL,20,Alabama,True
    50F6DDCA-C75C-4AFE-A024-0D2A0BF9D6CC,RefState,ceds.ed.gov,AR,30,Arkansas,True
    EA24B73C-B071-453B-9E8A-8BD6E1AE19B8,RefState,ceds.ed.gov,AS,40,American Samoa,True
    F24214B4-5DED-44D0-B29B-321BE28BCB93,RefState,ceds.ed.gov,AZ,50,Arizona,True
    FC8D5952-EF82-465A-9D0B-62A06C58C0EE,RefState,ceds.ed.gov,CA,60,California,True
    4A08E734-6101-4C0D-A066-E65F9183ED8A,RefState,ceds.ed.gov,CO,70,Colorado,True
    05950FFE-C9F6-4918-8362-E7B7A5202C3C,RefState,ceds.ed.gov,CT,80,Connecticut,True
    526B4BFB-5A10-40F5-BF4B-9704567AEF4D,RefState,ceds.ed.gov,DC,90,District of Columbia,True
    9D61F8B8-EF3D-40EF-81CE-B59F69632F53,RefState,ceds.ed.gov,DE,100,Delaware,True
    4FCAF288-4928-4450-8793-9852C29C2315,RefState,ceds.ed.gov,FL,110,Florida,True
    35B9C40A-617F-4633-AA76-A56D5147E89E,RefState,ceds.ed.gov,FM,120,Federated States of Micronesia,True
    FF5BC2E2-1D44-4B7B-8467-7643A6ABA583,RefState,ceds.ed.gov,GA,130,Georgia,True
    4A38E332-EA89-4625-86D8-016B0628CA9C,RefState,ceds.ed.gov,GU,140,Guam,True
    51F07FB9-AE06-4F3C-A8F2-99BAA9F143C2,RefState,ceds.ed.gov,HI,150,Hawaii,True
    744C35E4-8B9F-43F2-BB8A-DDFBF860E581,RefState,ceds.ed.gov,IA,160,Iowa,True
    84ADEB70-7F0E-4EEC-AC69-61C3EB5186D6,RefState,ceds.ed.gov,ID,170,Idaho,True
    2770B048-41B8-4ADC-AC7D-359BE9CA77D3,RefState,ceds.ed.gov,IL,180,Illinois,True
    55D9B58E-7FAA-4D83-8DCC-5C2D9D905444,RefState,ceds.ed.gov,IN,190,Indiana,True
    D3B16F02-6C56-4D72-8088-23A56C8C353A,RefState,ceds.ed.gov,KS,200,Kansas,True
    85F3BB5F-533D-4104-813C-8A5BAC6BED76,RefState,ceds.ed.gov,KY,210,Kentucky,True
    D3355BB2-71AE-43C8-93A4-8A94AD3D368A,RefState,ceds.ed.gov,LA,220,Louisiana,True
    994F7CFE-D3CA-4B25-9331-630DF404BACC,RefState,ceds.ed.gov,MA,230,Massachusetts,True
    3F854FB2-918B-495D-9B6C-7E68975A5FB3,RefState,ceds.ed.gov,MD,240,Maryland,True
    E8E5C5DD-6C00-4D79-91F0-9667C191D53D,RefState,ceds.ed.gov,ME,250,Maine,True
    91AEB1E0-02AD-43AC-BBDA-C6C6F2EB8229,RefState,ceds.ed.gov,MH,260,Marshall Islands,True
    8D5F6125-EDC8-4617-8625-CDCA447F0210,RefState,ceds.ed.gov,MI,270,Michigan,True
    92093A91-AD63-4C8E-A241-54791538B51C,RefState,ceds.ed.gov,MN,280,Minnesota,True
    975C4751-E25F-4268-AB1B-8802640ACE08,RefState,ceds.ed.gov,MO,290,Missouri,True
    975F8937-3322-4ED9-8C58-D0B3BF3C7791,RefState,ceds.ed.gov,MP,300,Northern Marianas,True
    D3C60549-CF5A-4763-9144-7FC62036954A,RefState,ceds.ed.gov,MS,310,Mississippi,True
    773E67E2-B0BB-4756-BD7B-9483B2F40FEE,RefState,ceds.ed.gov,MT,320,Montana,True
    D58CA3A6-6C82-4661-95DF-01ACE1075C96,RefState,ceds.ed.gov,NC,330,North Carolina,True
    64444C9E-FBD7-419A-B0A7-58746793AC6E,RefState,ceds.ed.gov,ND,340,North Dakota,True
    98934449-5343-46B9-898C-43E1E7C19032,RefState,ceds.ed.gov,NE,350,Nebraska,True
    05339530-6CD1-43D0-8674-F7873C567D1A,RefState,ceds.ed.gov,NH,360,New Hampshire,True
    A3B84025-5BA8-4229-8A11-0C518C1F4286,RefState,ceds.ed.gov,NJ,370,New Jersey,True
    FC843EF9-169A-4D5E-90BB-5F19CB919638,RefState,ceds.ed.gov,NM,380,New Mexico,True
    80555E2E-3A9F-4602-A90B-BF440C1ACCD4,RefState,ceds.ed.gov,NV,390,Nevada,True
    E2ACE706-5524-413E-8164-6D74C4FDB2EC,RefState,ceds.ed.gov,NY,400,New York,True
    7ECFD541-1962-4D01-BB86-5DD85766DD1D,RefState,ceds.ed.gov,OH,410,Ohio,True
    3B66E105-18F3-4067-ACD7-6A055FB162C7,RefState,ceds.ed.gov,OK,420,Oklahoma,True
    687A5C51-5F34-40E6-B329-1ADAEC370CD7,RefState,ceds.ed.gov,OR,430,Oregon,True
    DE4620E9-7C57-4065-8DBD-9F767DDD7B88,RefState,ceds.ed.gov,PA,440,Pennsylvania,True
    91FBFF8C-B029-45C2-82FE-BFF8C87FDCA8,RefState,ceds.ed.gov,PR,450,Puerto Rico,True
    67A9EB33-C9E3-413E-B3D0-B00F26007A8E,RefState,ceds.ed.gov,PW,460,Palau,True
    27B5FF55-80B3-4048-BACC-CA9A3C9DD3C4,RefState,ceds.ed.gov,RI,470,Rhode Island,True
    26A7361D-2B27-4DE9-BCF7-AD03DBDEAA52,RefState,ceds.ed.gov,SC,480,South Carolina,True
    21F4366B-9C35-4923-A3F7-45A4559DED6D,RefState,ceds.ed.gov,SD,490,South Dakota,True
    DDD79C61-65F2-44AF-97C0-ED6E3B2AB65A,RefState,ceds.ed.gov,TN,500,Tennessee,True
    06A57A29-DA3B-4A07-A8EB-9FA551405AB0,RefState,ceds.ed.gov,TX,510,Texas,True
    4054F216-1E39-4FB8-ACAA-A9C3CC7824FB,RefState,ceds.ed.gov,UT,520,Utah,True
    9A64EDAD-4DDE-43D6-A7E3-3E5A457787C5,RefState,ceds.ed.gov,VA,530,Virginia,True
    6EA96E1A-8F15-4B2B-A6E3-93981E62C889,RefState,ceds.ed.gov,VI,540,Virgin Islands,True
    98935CC0-B2E6-4120-A4CE-7B3CA18EB32D,RefState,ceds.ed.gov,VT,550,Vermont,True
    2C1F84CE-FF58-492A-87EC-12B37A360DAD,RefState,ceds.ed.gov,WA,560,Washington,True
    D1C6EEF1-B2A6-46CF-89A6-47E8BA2F969F,RefState,ceds.ed.gov,WI,570,Wisconsin,True
    FA5DC2DC-DF72-4052-BE05-BC540196A154,RefState,ceds.ed.gov,WV,580,West Virginia,True
    426A37AD-A542-4C9D-91C0-26F3D2D4AF42,RefState,ceds.ed.gov,WY,590,Wyoming,True
    36BCBFE1-7EFA-420E-8FDC-9FED29376B16,RefState,ceds.ed.gov,AA,600,Armed Forces America,True
    0C9210A8-8728-45C9-BE0C-3E93996BAD3F,RefState,ceds.ed.gov,AE,610,"Armed Forces Africa, Canada, Europe, and Mideast",True
    1B1D8C7A-7DA4-4DEB-B6FB-D75951B0C4B7,RefState,ceds.ed.gov,AP,620,Armed Forces Pacific,True
    D27CC7C7-B509-4C5D-A19E-296DEB840B0D,RefCountry,ceds.ed.gov,AF,10,AFGHANISTAN,True
    C4248C85-E6A3-4003-946F-4F8A1465823C,RefCountry,ceds.ed.gov,AX,20,ÅLAND ISLANDS,True
    BAF71D44-906B-4725-9525-095861DB192C,RefCountry,ceds.ed.gov,AL,30,ALBANIA,True
    6ED4915A-5F71-471A-B45B-09DB8C9BD6FA,RefCountry,ceds.ed.gov,DZ,40,ALGERIA,True
    FBCB6596-3A6A-4AFB-AB7F-AFCB85C48674,RefCountry,ceds.ed.gov,AS,50,AMERICAN SAMOA,True
    B875C46B-C971-4C34-B688-4D2CFB4D8901,RefCountry,ceds.ed.gov,AD,60,ANDORRA,True
    D58E52A1-669A-4D3D-B3F2-BFB487083E99,RefCountry,ceds.ed.gov,AO,70,ANGOLA,True
    6D5F15DA-1BCE-43F6-976E-AA4A9760CF26,RefCountry,ceds.ed.gov,AI,80,ANGUILLA,True
    D8516776-672C-4806-BEA2-57C9C932D0B4,RefCountry,ceds.ed.gov,AQ,90,ANTARCTICA,True
    1AF6BB03-DDBF-4A06-BB0B-7E2DD435EF00,RefCountry,ceds.ed.gov,AG,100,ANTIGUA AND BARBUDA,True
    3E489A05-9414-4905-876A-48E6B087DD7C,RefCountry,ceds.ed.gov,AR,110,ARGENTINA,True
    C95C52A4-06DD-481D-8067-E420C45AF05B,RefCountry,ceds.ed.gov,AM,120,ARMENIA,True
    218A0515-0DF9-4A79-8A5C-7235CEA3D133,RefCountry,ceds.ed.gov,AW,130,ARUBA,True
    4D36A8CE-7236-42A9-ADB3-2CAC9A6E0A8A,RefCountry,ceds.ed.gov,AU,140,AUSTRALIA,True
    D5FBCC82-E6B9-4A7B-9C81-BE91C3BF3051,RefCountry,ceds.ed.gov,AT,150,AUSTRIA,True
    86454B57-D0DC-4B5F-990B-35A073B725D7,RefCountry,ceds.ed.gov,AZ,160,AZERBAIJAN,True
    C71E4CF0-43D1-4C5B-9B3B-5BAE9768B659,RefCountry,ceds.ed.gov,BS,170,BAHAMAS,True
    431FD1D5-0C81-4519-871B-462125EB423F,RefCountry,ceds.ed.gov,BH,180,BAHRAIN,True
    610B665A-62D2-4043-BD42-ABB357D215F1,RefCountry,ceds.ed.gov,BD,190,BANGLADESH,True
    F7FD3C44-EF3A-4DCD-9FF8-BF1A6F511F15,RefCountry,ceds.ed.gov,BB,200,BARBADOS,True
    35606A50-C1B3-467F-BEBA-F9090248EC13,RefCountry,ceds.ed.gov,BY,210,BELARUS,True
    6B7A07BF-4F9C-4989-9EBD-113E314D94A9,RefCountry,ceds.ed.gov,BE,220,BELGIUM,True
    053D2AEC-28D7-4657-B6F9-2618ECB66435,RefCountry,ceds.ed.gov,BZ,230,BELIZE,True
    9DEC5368-A1CA-43A4-A811-79636D63C4CD,RefCountry,ceds.ed.gov,BJ,240,BENIN,True
    0C40619F-73BE-482A-B0FC-94C65B65E5EE,RefCountry,ceds.ed.gov,BM,250,BERMUDA,True
    AC73ED1A-8EBB-4FDC-9446-26313A9FCFDC,RefCountry,ceds.ed.gov,BT,260,BHUTAN,True
    CFBE2FDB-0DB5-4C0E-8D3B-082E13FC0769,RefCountry,ceds.ed.gov,BO,270,BOLIVIA (PLURINATIONAL STATE OF),True
    E9464C45-7AF9-4F70-B1C8-2799519C9AC4,RefCountry,ceds.ed.gov,BQ,280,"BONAIRE, SINT EUSTATIUS AND SABA",True
    66AFEF2A-AAAC-403D-986A-D30131D0800B,RefCountry,ceds.ed.gov,BA,290,BOSNIA AND HERZEGOVINA,True
    BF83057A-817C-46DD-9D96-B880D4A43632,RefCountry,ceds.ed.gov,BW,300,BOTSWANA,True
    19BA7D54-5564-4089-900B-E4A876F501ED,RefCountry,ceds.ed.gov,BV,310,BOUVET ISLAND,True
    E67825BB-F50A-4113-A0C9-E491254B761D,RefCountry,ceds.ed.gov,BR,320,BRAZIL,True
    35D3248A-7192-439A-A124-A47EE8C5E22A,RefCountry,ceds.ed.gov,IO,330,BRITISH INDIAN OCEAN TERRITORY,True
    5526EDE2-3618-4A09-9C85-6989FBDB0EB9,RefCountry,ceds.ed.gov,BN,340,BRUNEI DARUSSALAM,True
    F835BE43-A886-4B6F-8FBB-FAE8037DA7FE,RefCountry,ceds.ed.gov,BG,350,BULGARIA,True
    F4619148-DE08-431B-9F20-0AFCB4B0F381,RefCountry,ceds.ed.gov,BF,360,BURKINA FASO,True
    41DAA537-F493-4613-A939-3854BBF6633C,RefCountry,ceds.ed.gov,BI,370,BURUNDI,True
    FA8DA2A4-1B94-4768-A0CD-087FE2C3A57C,RefCountry,ceds.ed.gov,KH,380,CAMBODIA,True
    D10579AF-BB48-4EFF-A28F-A08E67A8F38A,RefCountry,ceds.ed.gov,CM,390,CAMEROON,True
    9FDB4302-095B-4CB8-BB21-38E92391CCE7,RefCountry,ceds.ed.gov,CA,400,CANADA,True
    F00048DE-EAE4-4401-A346-3048E028F919,RefCountry,ceds.ed.gov,CV,410,CABO VERDE,True
    C493E32C-145B-468F-BFBC-178D3617FE1F,RefCountry,ceds.ed.gov,KY,420,CAYMAN ISLANDS,True
    943FF087-293A-48FC-B7E6-24A3CACA52AC,RefCountry,ceds.ed.gov,CF,430,CENTRAL AFRICAN REPUBLIC,True
    FDEB4792-0633-41CA-AB8B-8B316DB92630,RefCountry,ceds.ed.gov,TD,440,CHAD,True
    1C97B8BE-2418-4B72-925B-21486B9CAFEF,RefCountry,ceds.ed.gov,CL,450,CHILE,True
    770CB099-B1FB-4E4B-B7EB-89DD0BAA15B6,RefCountry,ceds.ed.gov,CN,460,CHINA,True
    22C29EDF-B3F5-4E84-98BF-68B0B73806C6,RefCountry,ceds.ed.gov,CX,470,CHRISTMAS ISLAND,True
    7B7BC7C3-3B56-4F4A-B5DD-49583FBD798A,RefCountry,ceds.ed.gov,CC,480,COCOS (KEELING) ISLANDS,True
    30EA0E0A-06C2-456E-9062-B1527AF18514,RefCountry,ceds.ed.gov,CO,490,COLOMBIA,True
    8120B8A8-A113-44FD-8AE7-C0BFC05E3EAB,RefCountry,ceds.ed.gov,KM,500,COMOROS,True
    1F4F8956-5A23-4185-A244-5DDAF2C4A8D5,RefCountry,ceds.ed.gov,CG,510,CONGO,True
    D81156CD-C2DF-4BF4-B5E0-91A7D495D1F2,RefCountry,ceds.ed.gov,CD,520,"CONGO, DEMOCRATIC REPUBLIC OF THE",True
    EA6D2CD0-4457-4752-AC10-2AD8C2192DFD,RefCountry,ceds.ed.gov,CK,530,COOK ISLANDS,True
    1EE80E7F-CE07-4192-BC71-92CCE5DF5B87,RefCountry,ceds.ed.gov,CR,540,COSTA RICA,True
    7D626101-21A0-48FB-A209-374636012EFA,RefCountry,ceds.ed.gov,CI,550,CÔTE D'IVOIRE,True
    2976CDB1-2EBE-4FED-A988-5EA8166DA16D,RefCountry,ceds.ed.gov,HR,560,CROATIA,True
    31B0ED95-2375-4E9D-8BA6-09F36FE4B303,RefCountry,ceds.ed.gov,CU,570,CUBA,True
    3444FFC6-75DC-4BFD-A65F-C981B09A4E5D,RefCountry,ceds.ed.gov,CW,580,CURAÇAO,True
    7303FDD1-C6C0-4328-8487-DB1E31922014,RefCountry,ceds.ed.gov,CY,590,CYPRUS,True
    58D2376A-3B7E-4325-B238-080724BF7371,RefCountry,ceds.ed.gov,CZ,600,CZECH REPUBLIC,True
    0279764E-EB81-4FC2-A027-AA18205E624E,RefCountry,ceds.ed.gov,DK,610,DENMARK,True
    0D2664E5-F193-448F-8379-71A4B7B35751,RefCountry,ceds.ed.gov,DJ,620,DJIBOUTI,True
    122C7D71-0875-45E6-BF67-592327F0EA3E,RefCountry,ceds.ed.gov,DM,630,DOMINICA,True
    275978E1-6AEC-40D1-B9EF-5FD7109F249F,RefCountry,ceds.ed.gov,DO,640,DOMINICAN REPUBLIC,True
    679BBA36-AE9E-4790-B6FA-8C4BF1DE1691,RefCountry,ceds.ed.gov,EC,650,ECUADOR,True
    55B12FE3-A9DD-4487-8BD9-F1F5AA8BE5BD,RefCountry,ceds.ed.gov,EG,660,EGYPT,True
    76B0ECDC-2393-41D8-83D2-5543017B43EA,RefCountry,ceds.ed.gov,SV,670,EL SALVADOR,True
    1F5F7272-EE24-4BFB-9021-65DCDD641B47,RefCountry,ceds.ed.gov,GQ,680,EQUATORIAL GUINEA,True
    39963E26-F3A7-4197-B258-8B5E031DBC91,RefCountry,ceds.ed.gov,ER,690,ERITREA,True
    A42681D9-4185-4D8E-8F47-165D9D60DF2D,RefCountry,ceds.ed.gov,EE,700,ESTONIA,True
    45963F45-7BAF-4D51-99F4-C71EAF3DD152,RefCountry,ceds.ed.gov,ET,710,ETHIOPIA,True
    6CF21A67-DDD5-447F-9154-B4BDB8C886E9,RefCountry,ceds.ed.gov,FK,720,FALKLAND ISLANDS (MALVINAS),True
    2E42F906-C8AA-432D-8EC6-AA4F07B3A98F,RefCountry,ceds.ed.gov,FO,730,FAROE ISLANDS,True
    6F9646D1-CAE1-47BC-8E41-C82743997ACF,RefCountry,ceds.ed.gov,FJ,740,FIJI,True
    428DE3F9-D201-4BD4-98CA-F0F92B127C0D,RefCountry,ceds.ed.gov,FI,750,FINLAND,True
    281C8F83-1AB0-4678-B3AC-1E6DA98A1B8D,RefCountry,ceds.ed.gov,FR,760,FRANCE,True
    6F8A17F4-006C-4DF0-95BE-2344577B4C87,RefCountry,ceds.ed.gov,GF,770,FRENCH GUIANA,True
    0CAC2EF1-59E6-4390-9371-9EC5F400D3CA,RefCountry,ceds.ed.gov,PF,780,FRENCH POLYNESIA,True
    2CD7DC70-F061-4845-B626-24E8C4076FE5,RefCountry,ceds.ed.gov,TF,790,FRENCH SOUTHERN TERRITORIES,True
    105F3434-B6ED-457B-B395-B0BA7ED2EBD0,RefCountry,ceds.ed.gov,GA,800,GABON,True
    3E0BA96F-0121-4C51-ADC4-5B0B840C720F,RefCountry,ceds.ed.gov,GM,810,GAMBIA,True
    9E8290AE-90C6-4D4A-8F6A-B7C5B2BED017,RefCountry,ceds.ed.gov,GE,820,GEORGIA,True
    8E28378A-05A3-4EEB-A9ED-C3B1695BBC00,RefCountry,ceds.ed.gov,DE,830,GERMANY,True
    73C7F8FB-CC15-4ED7-9D4C-0B9B5054DABC,RefCountry,ceds.ed.gov,GH,840,GHANA,True
    4A91F599-1CEB-47DA-9655-239F7414BF49,RefCountry,ceds.ed.gov,GI,850,GIBRALTAR,True
    549ED6FA-054D-4E88-94A8-9A8CCD6A3A93,RefCountry,ceds.ed.gov,GR,860,GREECE,True
    4AD8D4C1-2AA5-4F4B-85BF-0FBB2E0463BB,RefCountry,ceds.ed.gov,GL,870,GREENLAND,True
    3AF9FCF6-15D7-451B-9355-702CB458AD29,RefCountry,ceds.ed.gov,GD,880,GRENADA,True
    FD1FE91D-640F-4029-A2A7-1C85E939E37C,RefCountry,ceds.ed.gov,GP,890,GUADELOUPE,True
    1FE1E74B-E294-4ADD-BF3A-5B4598C7C2CC,RefCountry,ceds.ed.gov,GU,900,GUAM,True
    37F47BB7-4866-4052-8531-F70C6CC05509,RefCountry,ceds.ed.gov,GT,910,GUATEMALA,True
    31737278-DDE3-4D14-B5BB-71ED800FD70D,RefCountry,ceds.ed.gov,GG,920,GUERNSEY,True
    596BE35E-82B8-4350-B18A-76BAF253518D,RefCountry,ceds.ed.gov,GN,930,GUINEA,True
    0A18754D-613A-4B3A-AB0E-CE0147035400,RefCountry,ceds.ed.gov,GW,940,GUINEA-BISSAU,True
    894E840B-6BF1-4714-B1C1-5F86F1465E09,RefCountry,ceds.ed.gov,GY,950,GUYANA,True
    C3AB650B-E895-4B45-956F-D4A21DE16762,RefCountry,ceds.ed.gov,HT,960,HAITI,True
    A9063AF1-0FA1-40C5-BF1B-3C5025C1E226,RefCountry,ceds.ed.gov,HM,970,HEARD ISLAND AND MCDONALD ISLANDS,True
    5382AB70-5BC5-4EE5-AC89-74222EB063E9,RefCountry,ceds.ed.gov,VA,980,HOLY SEE,True
    501E2372-EAAC-4DAA-B5F8-498BB79B5D06,RefCountry,ceds.ed.gov,HN,990,HONDURAS,True
    4566DA89-2577-421F-A7D4-BE159101CA25,RefCountry,ceds.ed.gov,HK,1000,HONG KONG,True
    17F05B32-C93E-4B65-B97B-47739D7BE2B6,RefCountry,ceds.ed.gov,HU,1010,HUNGARY,True
    0B407879-7D92-47F0-AD86-655E40283F93,RefCountry,ceds.ed.gov,IS,1020,ICELAND,True
    922A1996-C5E6-4A8E-A2B4-CA61DD3F12BC,RefCountry,ceds.ed.gov,IN,1030,INDIA,True
    509756FB-94BF-431D-B96E-9EC18A27298C,RefCountry,ceds.ed.gov,ID,1040,INDONESIA,True
    85056B48-EB0B-4CA9-8015-116311F92A53,RefCountry,ceds.ed.gov,IR,1050,IRAN (ISLAMIC REPUBLIC OF),True
    E47C2972-2934-48B8-A26E-A078AF162E45,RefCountry,ceds.ed.gov,IQ,1060,IRAQ,True
    F7F3EC17-D221-4AD4-AEE4-1155F0487A69,RefCountry,ceds.ed.gov,IE,1070,IRELAND,True
    73DF0854-8482-4AC8-81AA-AD5B6C4CF02D,RefCountry,ceds.ed.gov,IM,1080,ISLE OF MAN,True
    F9F71EBE-27D8-4CF1-945E-65A1CD978236,RefCountry,ceds.ed.gov,IL,1090,ISRAEL,True
    B653EDC2-B645-4BA6-889E-6F20DE6B6001,RefCountry,ceds.ed.gov,IT,1100,ITALY,True
    751AC8A6-FF95-403B-9CC2-2894B726B76A,RefCountry,ceds.ed.gov,JM,1110,JAMAICA,True
    A0A473A1-E41E-4C2B-A600-16607A1FB7FE,RefCountry,ceds.ed.gov,JP,1120,JAPAN,True
    04788D74-1C8D-40DD-B2CD-CDE1D73FED54,RefCountry,ceds.ed.gov,JE,1130,JERSEY,True
    5BA9655E-CC02-4E69-B586-1072DF66757B,RefCountry,ceds.ed.gov,JO,1140,JORDAN,True
    3F5F2153-0E28-48C9-8D6D-805867AC67AB,RefCountry,ceds.ed.gov,KZ,1150,KAZAKHSTAN,True
    479CE3D3-5DD5-4480-A1EB-A830439D329F,RefCountry,ceds.ed.gov,KE,1160,KENYA,True
    327A46E4-9608-43D5-99A4-6841865FB4DB,RefCountry,ceds.ed.gov,KI,1170,KIRIBATI,True
    75E9610E-0B9E-4340-B66F-8E405ED76662,RefCountry,ceds.ed.gov,KP,1180,KOREA (DEMOCRATIC PEOPLE'S REPUBLIC OF),True
    AD688E73-BC4A-4417-9B7F-387BB0B665AA,RefCountry,ceds.ed.gov,KR,1190,"KOREA, REPUBLIC OF",True
    F3B92EB3-4413-4E40-8748-742814C488FB,RefCountry,ceds.ed.gov,KW,1200,KUWAIT,True
    167F86C4-8C7B-4299-A1A6-C8AF9AB67DBE,RefCountry,ceds.ed.gov,KG,1210,KYRGYZSTAN,True
    D4844D61-AC72-4D42-B977-AC91738BBD4B,RefCountry,ceds.ed.gov,LA,1220,LAO PEOPLE'S DEMOCRATIC REPUBLIC,True
    D399E902-AF94-4531-A52C-D956D0B7C55C,RefCountry,ceds.ed.gov,LV,1230,LATVIA,True
    0724E62D-DF7D-43DE-B88D-C6D7790603A0,RefCountry,ceds.ed.gov,LB,1240,LEBANON,True
    30C1236C-2A1B-40E5-8E47-9C5CB1BEB8D3,RefCountry,ceds.ed.gov,LS,1250,LESOTHO,True
    22E384DE-DCE8-43A9-9373-7EA91F1D729A,RefCountry,ceds.ed.gov,LR,1260,LIBERIA,True
    7C70F8B1-1D8A-48CA-BA4E-888276B155D5,RefCountry,ceds.ed.gov,LY,1270,LIBYA,True
    30521C6A-BA6B-4B8B-A0D3-C1D1F0F38EDF,RefCountry,ceds.ed.gov,LI,1280,LIECHTENSTEIN,True
    0B9965B2-6D41-4AA4-A860-96B4D6AE2BC5,RefCountry,ceds.ed.gov,LT,1290,LITHUANIA,True
    795B7E23-49FA-4851-9228-5816BDC3C3A0,RefCountry,ceds.ed.gov,LU,1300,LUXEMBOURG,True
    1F000974-CD71-4789-B5C8-7DEDE2BF4354,RefCountry,ceds.ed.gov,MO,1310,MACAO,True
    7E2F4872-EC4A-4922-BE59-7E8E510319C3,RefCountry,ceds.ed.gov,MK,1320,"MACEDONIA, THE FORMER YUGOSLAV REPUBLIC OF",True
    CB6825D4-A079-41DC-9511-D30AB3D9D8A0,RefCountry,ceds.ed.gov,MG,1330,MADAGASCAR,True
    DAB841AE-A8D0-4B53-81C7-71CAA144BB79,RefCountry,ceds.ed.gov,MW,1340,MALAWI,True
    55CD15C5-0B88-4B3F-88EA-2378A055B0E6,RefCountry,ceds.ed.gov,MY,1350,MALAYSIA,True
    5DF7FD05-9BAB-4271-8AB4-A101656B99B7,RefCountry,ceds.ed.gov,MV,1360,MALDIVES,True
    F38D0885-53A7-42C6-8923-1945E6BB924A,RefCountry,ceds.ed.gov,ML,1370,MALI,True
    C96DFCAD-A2E6-4CCE-AC7D-BAAAEE4E2A5E,RefCountry,ceds.ed.gov,MT,1380,MALTA,True
    47BBD0B0-FF49-4E7B-8022-5497DF5BA5C2,RefCountry,ceds.ed.gov,MH,1390,MARSHALL ISLANDS,True
    B906FFA3-4C09-44D8-90B5-227D3B90CFD0,RefCountry,ceds.ed.gov,MQ,1400,MARTINIQUE,True
    59EDC14B-E7F5-46C2-9F5C-F9569B5348A2,RefCountry,ceds.ed.gov,MR,1410,MAURITANIA,True
    7E628BC1-2BB6-48C6-A210-4FD9677FAB9B,RefCountry,ceds.ed.gov,MU,1420,MAURITIUS,True
    1AF13DD5-50E8-45AF-AAE4-4E45AA7CDA0E,RefCountry,ceds.ed.gov,YT,1430,MAYOTTE,True
    86111F48-2681-44B5-BEC7-1B46F834C567,RefCountry,ceds.ed.gov,MX,1440,MEXICO,True
    453FA007-D61C-4D1B-B6DC-CFD74313698C,RefCountry,ceds.ed.gov,FM,1450,MICRONESIA (FEDERATED STATES OF),True
    01FDAC40-AF6F-477D-890D-8500DCC4432E,RefCountry,ceds.ed.gov,MD,1460,"MOLDOVA, REPUBLIC OF",True
    0061C812-8A47-49DA-AE14-074386532A8F,RefCountry,ceds.ed.gov,MC,1470,MONACO,True
    466CD301-592F-4480-9153-ECA53DC2DA2B,RefCountry,ceds.ed.gov,MN,1480,MONGOLIA,True
    410F008B-CDA4-4609-A8AC-91DBF38EAE34,RefCountry,ceds.ed.gov,ME,1490,MONTENEGRO,True
    B2411F7B-7BD3-4A93-9321-80661F7732E1,RefCountry,ceds.ed.gov,MS,1500,MONTSERRAT,True
    E65079E9-6064-43F5-A9F3-797CB5DE8A0E,RefCountry,ceds.ed.gov,MA,1510,MOROCCO,True
    89C048D5-9BD1-47A5-BDAA-9B4E58B22C48,RefCountry,ceds.ed.gov,MZ,1520,MOZAMBIQUE,True
    5A666073-4114-4C83-9614-A28161BE68FC,RefCountry,ceds.ed.gov,MM,1530,MYANMAR,True
    C262EBC2-14AC-4C7E-8333-4908FDA99F7A,RefCountry,ceds.ed.gov,NA,1540,NAMIBIA,True
    1C352B2F-F6F0-401A-82A6-837187B393BB,RefCountry,ceds.ed.gov,NR,1550,NAURU,True
    FD689F22-09BB-4A3C-AD17-055BF3B3B16C,RefCountry,ceds.ed.gov,NP,1560,NEPAL,True
    8F9679A5-1B7A-4C35-9297-FCD4AF94CB12,RefCountry,ceds.ed.gov,NL,1570,NETHERLANDS,True
    EE4E2F96-15AC-44FA-AA43-7ED8903A467D,RefCountry,ceds.ed.gov,NC,1580,NEW CALEDONIA,True
    A016256C-E7F3-4B9F-9897-0AC80CED7A8D,RefCountry,ceds.ed.gov,NZ,1590,NEW ZEALAND,True
    14C3C6C1-65E7-46AA-AA0D-A46428C6A7A4,RefCountry,ceds.ed.gov,NI,1600,NICARAGUA,True
    0706A939-1EF8-45C9-AE0F-6C4E16442B3A,RefCountry,ceds.ed.gov,NE,1610,NIGER,True
    AA8D132E-F753-4699-AC6B-5975AB620C81,RefCountry,ceds.ed.gov,NG,1620,NIGERIA,True
    400A1956-D7C2-4207-BD4B-24DDAA4BEF74,RefCountry,ceds.ed.gov,NU,1630,NIUE,True
    E388E2DB-9EAF-4B9E-AB8E-64CD118BB19F,RefCountry,ceds.ed.gov,NF,1640,NORFOLK ISLAND,True
    529DCFA0-3191-49D7-9C5A-430BBC7C72F1,RefCountry,ceds.ed.gov,MP,1650,NORTHERN MARIANA ISLANDS,True
    F6BB8EBD-13FC-492E-8C2F-12DEB51F4BC7,RefCountry,ceds.ed.gov,NO,1660,NORWAY,True
    4C19193D-BC67-4FCB-94D0-1D7E05C6D5BC,RefCountry,ceds.ed.gov,OM,1670,OMAN,True
    51E5415D-8663-40A0-92C7-85A4C90D726F,RefCountry,ceds.ed.gov,PK,1680,PAKISTAN,True
    7C9C9603-04D3-4076-969D-B0FF10DE00CA,RefCountry,ceds.ed.gov,PW,1690,PALAU,True
    4C5D8A77-B85E-4920-AB76-8F60D113BF81,RefCountry,ceds.ed.gov,PS,1700,"PALESTINE, STATE OF",True
    EF403E92-BF0A-499C-8BFC-F2AF26EEE0C8,RefCountry,ceds.ed.gov,PA,1710,PANAMA,True
    80BD56AF-3441-4A36-9E0A-275DE4CDFA43,RefCountry,ceds.ed.gov,PG,1720,PAPUA NEW GUINEA,True
    41E21101-03D8-4549-A6AC-499136490091,RefCountry,ceds.ed.gov,PY,1730,PARAGUAY,True
    51F14894-83C8-421B-B248-98567587BC9F,RefCountry,ceds.ed.gov,PE,1740,PERU,True
    B59CD07B-E6C0-4A64-8965-27DDF675E8B9,RefCountry,ceds.ed.gov,PH,1750,PHILIPPINES,True
    5C3F2B8C-D4D5-4CD7-84D6-E4596E1DD3B8,RefCountry,ceds.ed.gov,PN,1760,PITCAIRN,True
    F52D0D10-06DD-4937-80B1-0331A1C211CB,RefCountry,ceds.ed.gov,PL,1770,POLAND,True
    D7B2F40F-74F6-40C1-A02C-C9920B198526,RefCountry,ceds.ed.gov,PT,1780,PORTUGAL,True
    1EC79991-D73C-4B3F-9CC4-537DC68FC48F,RefCountry,ceds.ed.gov,PR,1790,PUERTO RICO,True
    46D0B925-44FB-46BD-9488-717888777756,RefCountry,ceds.ed.gov,QA,1800,QATAR,True
    6827FD44-246C-4F53-9320-17946A6B4017,RefCountry,ceds.ed.gov,RE,1810,RÉUNION,True
    C5101A5B-B94E-4E45-9291-AC5BF329CCB2,RefCountry,ceds.ed.gov,RO,1820,ROMANIA,True
    4F9A48C8-A04D-4F5D-9100-E7FD403BBE46,RefCountry,ceds.ed.gov,RU,1830,RUSSIAN FEDERATION,True
    5DB1879F-AE04-40FE-B3F2-13285D78216D,RefCountry,ceds.ed.gov,RW,1840,RWANDA,True
    F8124018-FD02-4763-A8B0-57D04084E94D,RefCountry,ceds.ed.gov,BL,1850,SAINT BARTHÉLEMY,True
    AA552BEE-7833-4A9C-AFE9-8DF0D4996950,RefCountry,ceds.ed.gov,SH,1860,"SAINT HELENA, ASCENSION AND TRISTAN DA CUNHA",True
    7E325754-D43B-4431-A17B-1F39BCBC6FCB,RefCountry,ceds.ed.gov,KN,1870,SAINT KITTS AND NEVIS,True
    993ED9DD-8902-413E-87F7-0A7F89AEB681,RefCountry,ceds.ed.gov,LC,1880,SAINT LUCIA,True
    4B927548-A011-4EA4-A807-E9C7CA9B8182,RefCountry,ceds.ed.gov,MF,1890,SAINT MARTIN (FRENCH PART),True
    9213514F-EF2F-41F1-819F-B5B9AA389DD8,RefCountry,ceds.ed.gov,PM,1900,SAINT PIERRE AND MIQUELON,True
    A76FAAD0-97CC-4C01-A33B-17A84963DF17,RefCountry,ceds.ed.gov,VC,1910,SAINT VINCENT AND THE GRENADINES,True
    02BF9BB8-2B0B-48DF-A44A-3F55C5E660CA,RefCountry,ceds.ed.gov,WS,1920,SAMOA,True
    B777595B-0E66-4597-81D0-2FA3524B3DAF,RefCountry,ceds.ed.gov,SM,1930,SAN MARINO,True
    AEEEBA86-00EB-4C50-91DC-0FD8BF63296C,RefCountry,ceds.ed.gov,ST,1940,SAO TOME AND PRINCIPE,True
    ABEEF49C-2E93-458A-84F1-2D5C77424539,RefCountry,ceds.ed.gov,SA,1950,SAUDI ARABIA,True
    94AD69A4-B71F-4FA9-91AE-F12BE09C81DE,RefCountry,ceds.ed.gov,SN,1960,SENEGAL,True
    BCA16B75-BF2E-497D-824C-9EA569BD08DA,RefCountry,ceds.ed.gov,RS,1970,SERBIA,True
    5FA3CF72-FFA4-40CE-8C4D-52793DBCBE64,RefCountry,ceds.ed.gov,SC,1980,SEYCHELLES,True
    0E5B7268-6612-4092-B075-7CE554F6AA8B,RefCountry,ceds.ed.gov,SL,1990,SIERRA LEONE,True
    0A490B99-2619-4F6A-AE5B-7F55869E569B,RefCountry,ceds.ed.gov,SG,2000,SINGAPORE,True
    9585295D-9F85-4A5D-804F-8A78212EFA7E,RefCountry,ceds.ed.gov,SX,2010,SINT MAARTEN (DUTCH PART),True
    C02772F6-4C93-4ADA-B30A-758A90AE7A2C,RefCountry,ceds.ed.gov,SK,2020,SLOVAKIA,True
    1D56E8EE-74CC-49D6-8174-9670E6356024,RefCountry,ceds.ed.gov,SI,2030,SLOVENIA,True
    A6425AC0-72D3-4008-8BBB-BEDC03F20AAA,RefCountry,ceds.ed.gov,SB,2040,SOLOMON ISLANDS,True
    AC26F682-2AC1-4907-B165-CAE046FC2BCA,RefCountry,ceds.ed.gov,SO,2050,SOMALIA,True
    A3D38931-C557-4530-902D-C27529532E7C,RefCountry,ceds.ed.gov,ZA,2060,SOUTH AFRICA,True
    F0B07ACA-C168-4152-B6AB-2B7EE0162D0E,RefCountry,ceds.ed.gov,GS,2070,SOUTH GEORGIA AND THE SOUTH SANDWICH ISLANDS,True
    930FB257-80FD-4410-91BE-0B047A0E9483,RefCountry,ceds.ed.gov,SS,2080,SOUTH SUDAN,True
    7C9A8ABA-B6A4-4B31-8CBE-6609D283322D,RefCountry,ceds.ed.gov,ES,2090,SPAIN,True
    ED6CE09B-5451-4215-922C-D5F1BD23D2C0,RefCountry,ceds.ed.gov,LK,2100,SRI LANKA,True
    E9A6F2AE-7BF4-4DA7-92AA-E8685030B1B5,RefCountry,ceds.ed.gov,SD,2110,SUDAN,True
    83D8D9EB-36E3-4081-9D3F-EFCB894B1EF0,RefCountry,ceds.ed.gov,SR,2120,SURINAME,True
    0C728176-8046-4390-A579-84E67D67B1E1,RefCountry,ceds.ed.gov,SJ,2130,SVALBARD AND JAN MAYEN,True
    FE5D4E7F-7E05-4018-89D1-4A2C3BA268A5,RefCountry,ceds.ed.gov,SZ,2140,SWAZILAND,True
    F63636C1-3123-4700-82CE-C4FD7EA9C289,RefCountry,ceds.ed.gov,SE,2150,SWEDEN,True
    0B958C09-33BF-47EF-B70E-C42E33FBDDC3,RefCountry,ceds.ed.gov,CH,2160,SWITZERLAND,True
    D0E968A9-B41A-4301-B7E2-41FAE7B597A2,RefCountry,ceds.ed.gov,SY,2170,SYRIAN ARAB REPUBLIC,True
    2F4865F0-C6E6-4C24-8D63-8095AE34B472,RefCountry,ceds.ed.gov,TW,2180,TAIWAN,True
    77867C67-1973-41AD-8824-C08AB2EF346E,RefCountry,ceds.ed.gov,TJ,2190,TAJIKISTAN,True
    3E8FFA2A-9A41-4ECF-AFFF-9BD16A555078,RefCountry,ceds.ed.gov,TZ,2200,"TANZANIA, UNITED REPUBLIC OF",True
    41767821-A02C-4218-9066-D026FFA3213C,RefCountry,ceds.ed.gov,TH,2210,THAILAND,True
    240F8689-9BE9-4883-82E5-4212B53DAB5B,RefCountry,ceds.ed.gov,TL,2220,TIMOR-LESTE,True
    B67AF7FD-9496-46CD-907A-5040F7A4D56C,RefCountry,ceds.ed.gov,TG,2230,TOGO,True
    03A40FA1-D42C-41D4-AC1C-A58A9309DC25,RefCountry,ceds.ed.gov,TK,2240,TOKELAU,True
    77C473E4-BC68-4341-8F32-C312DCA7BFE2,RefCountry,ceds.ed.gov,TO,2250,TONGA,True
    D07FBFC8-DE57-4D65-B0A3-2AC8CD6F12CA,RefCountry,ceds.ed.gov,TT,2260,TRINIDAD AND TOBAGO,True
    6E2BF916-718B-4FBC-AB54-DD4DEE4D91E0,RefCountry,ceds.ed.gov,TN,2270,TUNISIA,True
    50D8BE7D-2F24-4E3B-9E29-D75CF7177F19,RefCountry,ceds.ed.gov,TR,2280,TURKEY,True
    61AFB333-7B93-471E-A4B0-EE4FEC8588B7,RefCountry,ceds.ed.gov,TM,2290,TURKMENISTAN,True
    2BEB099D-61D0-4E8F-AF1F-96C1C781292C,RefCountry,ceds.ed.gov,TC,2300,TURKS AND CAICOS ISLANDS,True
    D8DA0877-CCB5-4963-9E26-308BF067320C,RefCountry,ceds.ed.gov,TV,2310,TUVALU,True
    BA5C6CDE-7D11-45AF-B30B-76500FA91425,RefCountry,ceds.ed.gov,UG,2320,UGANDA,True
    52ECB0E0-22B9-4267-BDDD-998BAB471EC6,RefCountry,ceds.ed.gov,UA,2330,UKRAINE,True
    EBF9A8F9-C0CC-4386-B221-25609FB31328,RefCountry,ceds.ed.gov,AE,2340,UNITED ARAB EMIRATES,True
    3B3D1E6C-28D7-4189-8C7F-607F0211969B,RefCountry,ceds.ed.gov,GB,2350,UNITED KINGDOM OF GREAT BRITAIN AND NORTHERN IRELAND,True
    B27E984F-0441-4833-8724-60E2496A47D7,RefCountry,ceds.ed.gov,US,2360,UNITED STATES OF AMERICA,True
    24D20FA9-94ED-43EB-AC99-0A2E3E0E3A73,RefCountry,ceds.ed.gov,UM,2370,UNITED STATES MINOR OUTLYING ISLANDS,True
    7EBF4E35-914B-4DB3-9827-08B9A4D3F45B,RefCountry,ceds.ed.gov,UY,2380,URUGUAY,True
    9F932DC2-F603-4B5E-8F12-0BDD1E6AB1B8,RefCountry,ceds.ed.gov,UZ,2390,UZBEKISTAN,True
    E8FDD235-C19F-4F0F-9300-78E5C22C70F2,RefCountry,ceds.ed.gov,VU,2400,VANUATU,True
    F4FCCBA2-DCD9-403A-AF1E-9450EDAA0BDD,RefCountry,ceds.ed.gov,VE,2410,VENEZUELA (BOLIVARIAN REPUBLIC OF),True
    F3CE298A-889D-4E33-B23B-0436D79AE5CA,RefCountry,ceds.ed.gov,VN,2420,VIET NAM,True
    8F01500D-B796-48A3-B18D-26FB561A0A63,RefCountry,ceds.ed.gov,VG,2430,VIRGIN ISLANDS (BRITISH),True
    4783FC4D-9665-4346-8C9D-4DA16D655DFF,RefCountry,ceds.ed.gov,VI,2440,VIRGIN ISLANDS (U.S.),True
    C98465F0-6A37-4D23-97FE-845E92F82823,RefCountry,ceds.ed.gov,WF,2450,WALLIS AND FUTUNA,True
    5CA05C14-7A46-4CF2-8E66-2A901E95ADE0,RefCountry,ceds.ed.gov,EH,2460,WESTERN SAHARA,True
    81539402-144E-46BC-9ED0-FF0C666FDE08,RefCountry,ceds.ed.gov,YE,2470,YEMEN,True
    2EB51FA4-1241-4614-87FE-190896B35849,RefCountry,ceds.ed.gov,ZM,2480,ZAMBIA,True
    F0F142DC-C1C0-425E-9961-E438DEDBEB57,RefCountry,ceds.ed.gov,ZW,2490,ZIMBABWE,True
    F772D02B-3B1E-41A4-941B-77BEBB2AF8B2,RefPersonRelationship,imsglobal.com,parent,10,Parent,True
    C9D0304D-A529-409A-9C4E-C008E76EFA6E,RefPersonRelationship,imsglobal.com,relative,20,Relative,True
    FE54C353-BFE9-4229-BDF7-F421423739A3,RefPersonRelationship,imsglobal.com,guardian,30,Guardian,True
    0D16FCED-6DC7-4235-90BF-724D40ABC7BD,RefStudentOrgRole,imsglobal.org,student,10,Student,True
    2BE22270-5236-41BF-B359-167E725F45DA,RefStaffOrgRole,imsglobal.org,aide,10,Aide,True
    96DB6F6A-B3C7-4A8C-8885-42AFC7598528,RefStaffOrgRole,imsglobal.org,proctor,20,Proctor,True
    03FFC8C5-9C64-4321-8041-334F07A252F0,RefStaffOrgRole,imsglobal.org,teacher,30,Teacher,True
    6A43802A-4372-44D3-B3F0-7B9BC24EF9D8,RefStaffOrgRole,imsglobal.org,administrator,40,Administrator,True
    DA004FFF-9B71-4926-9D7C-79B83B19F31B,RefStaffOrgRole,microsoft.com,itAdmin,50,IT Admin,True
    05DE1E52-6991-4F77-BBC6-620A7171E1A6,RefStaffOrgRole,microsoft.com,officeStaff,60,Office Staff,True
    57AA30CB-DAD3-4D73-B568-DFD0B431BD83,RefStaffOrgRole,microsoft.com,nurse,70,Nurse,True
    8F5976E5-3EFB-45E7-8751-89C83BB10D86,RefStaffOrgRole,microsoft.com,occupationalTherapist,80,Occupational Therapist,True
    DA01A84E-3E08-4047-996E-1240243825E6,RefStaffOrgRole,microsoft.com,physicalTherapist,90,Physical Therapist,True
    CAA12695-48A2-4EAF-9798-EDB972CF89F2,RefStaffOrgRole,microsoft.com,speechTherapist,100,Speech Therapist,True
    A5E30209-2416-47FF-BB2B-B30892A4544D,RefStaffOrgRole,microsoft.com,visionTherapist,110,Vision,True
    4F0164B4-3827-4993-AEF5-29B5CCEAFA48,RefStaffOrgRole,microsoft.com,paraprofessional,120,Paraprofessional,True
    329EF3DE-913A-45C2-B235-9B5BB9D1B576,RefStaffOrgRole,microsoft.com,teacherAssistant,130,Teacher Assistant,True
    BC319764-C1EB-4DFA-8C43-65C8C96B5BBF,RefStaffOrgRole,microsoft.com,staff,140,Staff,True
    D1CA502E-DB62-41D2-B438-AC669E6A9663,RefStudentSectionRole,imsglobal.org,student,10,Student,True
    38846D3C-397F-40BB-B43E-89092FFB7FAD,RefStaffSectionRole,imsglobal.org,aide,10,Aide,True
    453DD32F-1088-4BD4-9B0E-FD4AC325D676,RefStaffSectionRole,imsglobal.org,proctor,20,Proctor,True
    C943E793-2DB7-47C0-B187-A9ED65EEBD5B,RefStaffSectionRole,imsglobal.org,teacher,30,Teacher,True
    00574D97-8A98-454E-A879-9465A798CFE2,RefStaffSectionRole,microsoft.com,nurse,40,Nurse,True
    6960C6A5-E850-4547-BF15-762A7260F7D9,RefStaffSectionRole,microsoft.com,occupationalTherapist,50,Occupational Therapist,True
    F62E6FE1-DAC6-43D1-A6C9-EFB8429BA9C9,RefStaffSectionRole,microsoft.com,physicalTherapist,60,Physical Therapist,True
    BD3A443E-778B-4B6F-85F7-D6B6E30D1795,RefStaffSectionRole,microsoft.com,speechTherapist,70,Speech Therapist,True
    54970CC5-EE96-4A29-8A95-441109DEEBD0,RefStaffSectionRole,microsoft.com,visionTherapist,80,Vision,True
    7690289D-A685-4886-B5A4-122544100B20,RefStaffSectionRole,microsoft.com,paraprofessional,90,Paraprofessional,True
    C16353AD-902F-4CDC-86A5-30491A0612EA,RefStaffSectionRole,microsoft.com,teacherAssistant,100,Teacher Assistant,True
    BBE8A650-B452-4B05-9CB6-D800F08A5E3C,RefStaffSectionRole,microsoft.com,staff,110,Staff,True
    08DF30A4-DFF6-4EC9-8BDA-118F1B40FC4A,RefPersonGroupRole,microsoft.com,participant,10,Participant,True
    632D8FC9-DEC5-420E-B8F4-D6CCFC3349F6,RefPersonGroupRole,microsoft.com,coach,20,Coach,True
    E53285DE-8216-45C9-B0D0-3962883E425C,RefPersonGroupRole,microsoft.com,assistant,30,Assistant,True
    353ABDDA-19D6-4008-8C56-506C65900782,RefGradeLevel,ceds.ed.gov,IT,10,Infant/Toddler,True
    49EA747D-0A19-4EDF-BCFB-BB5F0166381F,RefGradeLevel,ceds.ed.gov,PR,20,Preschool,True
    72B89395-E9E3-4564-8DAF-88AEA58AFED3,RefGradeLevel,ceds.ed.gov,PK,30,Prekindergarten,True
    0CDED2E6-57B6-4A21-ABCC-1E3496DFB73E,RefGradeLevel,ceds.ed.gov,TK,40,Transitional Kindergarten,True
    B1DA4920-25D6-4561-9221-ED4352F6B1B5,RefGradeLevel,ceds.ed.gov,KG,50,Kindergarten,True
    6C0804DB-FF53-4CBB-88DC-BD00724A549E,RefGradeLevel,ceds.ed.gov,01,60,First grade,True
    F81116C9-B37C-405F-A463-9E6279442376,RefGradeLevel,ceds.ed.gov,02,70,Second grade,True
    E75F1B3A-3FFA-4E4D-8B55-6288F34FA491,RefGradeLevel,ceds.ed.gov,03,80,Third grade,True
    5C9C9038-3E99-4EFD-9AF7-4B2C465D9ACA,RefGradeLevel,ceds.ed.gov,04,90,Fourth grade,True
    490E900A-7629-47CD-B677-381718F9E2C4,RefGradeLevel,ceds.ed.gov,05,100,Fifth grade,True
    DF413EB6-47E5-46DD-88AF-6478B2854D4A,RefGradeLevel,ceds.ed.gov,06,110,Sixth grade,True
    6C2F76EA-5B22-4293-BA16-5216361AD233,RefGradeLevel,ceds.ed.gov,07,120,Seventh grade,True
    B106D95C-CA5E-457E-B848-3A231917C34C,RefGradeLevel,ceds.ed.gov,08,130,Eighth grade,True
    4429F333-536A-458F-AE87-FDF5471B5E8D,RefGradeLevel,ceds.ed.gov,09,140,Ninth grade,True
    B6747F48-667B-4F0D-8438-9D1B180A3791,RefGradeLevel,ceds.ed.gov,10,150,Tenth grade,True
    490702EA-9AC0-435E-AB8F-C1999BB0B393,RefGradeLevel,ceds.ed.gov,11,160,Eleventh grade,True
    37DB651A-E2CC-4C16-8F52-27D4FA17B680,RefGradeLevel,ceds.ed.gov,12,170,Twelfth grade,True
    8EDEF0A7-FE7A-48DD-A268-CA187E3986A5,RefGradeLevel,ceds.ed.gov,13,180,Grade 13,True
    9C833058-4DA4-46D8-BB96-9A389105205E,RefGradeLevel,ceds.ed.gov,PS,190,Postsecondary,True
    87DFDF97-B458-4F24-AD53-A1FEE4850309,RefGradeLevel,ceds.ed.gov,UG,200,Ungraded,True
    7C0F1F97-101A-4E77-BC41-BAB1CC336733,RefGradeLevel,ceds.ed.gov,Other,210,Other,True
    171E5E6E-4A6C-45B6-A185-1C8A63886B1C,RefRace,imsglobal.org,americanIndianOrAlaskaNative,10,American Indian or Alaska Native,True
    49870DDA-FAD1-468E-B81A-103EB6ACC807,RefRace,imsglobal.org,asian,20,Asian,True
    C417FFAF-9B5D-4809-9AD0-0CC88B334C1E,RefRace,imsglobal.org,blackOrAfricanAmerican,30,Black or African American,True
    1DE06A27-C07B-4BA4-9228-B76CD70A6148,RefRace,imsglobal.org,nativeHawaiianOrOtherPacificIslander,40,Native Hawaiian or Other Pacific Islander,True
    B953AE14-E0D1-47D3-B250-C72A8B0290DB,RefRace,imsglobal.org,white,50,White,True
    547E761B-45D4-4A24-B1D7-814E4ABA35C2,RefEthnicity,imsglobal.org,hispanicOrLatinoEthnicity,10,Hispanic or Latino Ethnicity,True
    08EAFC29-8F6D-4FF5-83A4-71B131D0E7DB,RefEnrollmentStatus,microsoft.com,ConcurrentlyEnrolled,10,Concurrently enrolled,True
    F36F047A-F410-4761-B41F-17B952A8EAD4,RefEnrollmentStatus,microsoft.com,CurrentlyEnrolled,10,Currently enrolled,True
    918F8FB7-D630-406F-BF04-62BF1255A148,RefEnrollmentStatus,microsoft.com,PreviouslyEnrolled,30,Previously enrolled,True
    BEC33C7F-01C1-41EA-818F-FBFDAE867EB7,RefEnrollmentStatus,microsoft.com,Transferring,40,Transferring (will enroll),True
    7DAF8820-6691-4D61-A210-CE94EA7D3667,RefIdentifierType,microsoft.com,ActiveDirectoryId,10,Active Directory Id,True
    DB231C72-7C41-4A65-9A3D-49B9F6CD78C4,RefIdentifierType,microsoft.com,Fed,20,Federal Id,True
    5D464768-0162-4B69-91CA-49F53AA0A474,RefIdentifierType,imsglobal.org,LTIId,30,LTI Id,True
    450E6525-61A6-4BF6-A3D5-F95EB5CB1183,RefIdentifierType,imsglobal.org,username,40,Username (OneRoster),True
    D787E8F6-4DD3-4C89-8293-CB3CDD0CC0A4,RefIdentifierType,imsglobal.org,identifier,50,Identifier (OneRoster),True
    CEEF7E8E-E083-4048-B3C0-E7D1EE37A4E6,RefSectionType,imsglobal.org,homeroom,10,Homeroom,True
    96669810-AB33-4B0F-92BE-6E2CC6F30EE9,RefSectionType,imsglobal.org,scheduled,20,Scheduled,True
    E5F838D4-21C3-4932-850C-0BE7B169A85C,RefPublicSchoolResidenceStatus,ceds.ed.gov,01652,10,Resident of administrative unit and usual school attendance area.,True
    901B2D88-967B-499B-91E8-9938CD03985F,RefPublicSchoolResidenceStatus,ceds.ed.gov,01653,20,"Resident of administrative unit, but of other school attendance area.",True
    EFB677F4-D913-4A7E-A59D-8DD426CA7256,RefPublicSchoolResidenceStatus,ceds.ed.gov,01654,30,"Resident of this state, but not of this administrative unit.",True
    3B5CBE72-809B-47C5-97BC-84EDF473CCFF,RefPublicSchoolResidenceStatus,ceds.ed.gov,01655,40,Resident of an administrative unit that crosses state boundaries.,True
    C5BA9B59-F4A3-4506-BA0E-7F5967292D7A,RefPublicSchoolResidenceStatus,ceds.ed.gov,01656,50,Resident of another state.,True
    BF84752E-4E3F-4B80-BED0-2DE4ABB355D5,RefRace,imsglobal.org,demographicRaceTwoOrMoreRaces,60,Designates multiple races,True
    4B969AD4-3DF0-4C81-B586-E08DB2F89974,RefAcademicSubject,nces.ed.gov,01,10,English Language and Literature,True
    DC5AE6F7-F7F7-4B0A-B838-C6A53947FC39,RefAcademicSubject,nces.ed.gov,02,20,Mathematics,True
    3621BA8C-DA33-4230-AE29-7A69A674CAA1,RefAcademicSubject,nces.ed.gov,03,30,Life and Physical Sciences,True
    3BCAA0B5-E890-4D44-9630-C2618FD8E872,RefAcademicSubject,nces.ed.gov,04,40,Social Sciences and History,True
    DD70C99E-4863-4E76-BDC1-998CEE2E6075,RefAcademicSubject,nces.ed.gov,05,50,Visual and Performing Arts,True
    0EFD2AC5-AA04-406D-BD9A-6C12602B4F44,RefAcademicSubject,nces.ed.gov,07,60,Religious Education and Theology,True
    6ACD32DE-CF55-4D57-8058-BEADA9FA6745,RefAcademicSubject,nces.ed.gov,08,70,"Physical, Health, and Safety Education",True
    FC6955CD-7355-41DC-A968-EE9BFBA51E19,RefAcademicSubject,nces.ed.gov,09,80,Military Science,True
    5956FCAC-86B1-4110-B041-37569BD48E52,RefAcademicSubject,nces.ed.gov,10,90,Information Technology,True
    B6EB7682-6A40-42E4-9963-AF9BB9890ECE,RefAcademicSubject,nces.ed.gov,11,100,Communication and Audio/Visual Technology,True
    956A937F-A4EA-433D-9736-750E969745E5,RefAcademicSubject,nces.ed.gov,12,110,Business and Marketing,True
    9F434285-9292-40F5-859D-715F1020AFFD,RefAcademicSubject,nces.ed.gov,13,120,Manufacturing,True
    480A0424-CBE9-43B3-AF7F-F8BC3D11FECE,RefAcademicSubject,nces.ed.gov,14,130,Health Care Sciences,True
    38BCFB35-1B7C-4E00-9F15-A9BB9347F7DE,RefAcademicSubject,nces.ed.gov,15,140,"Public, Protective, and Government Service",True
    22A4D31A-E5A2-4C92-84B1-1E924547E083,RefAcademicSubject,nces.ed.gov,16,150,Hospitality and Tourism,True
    49D3D99D-4AEE-4B59-B286-01978A458348,RefAcademicSubject,nces.ed.gov,17,160,Architecture and Construction,True
    3690A6BE-5A9E-4D50-A97C-0368EA998A77,RefAcademicSubject,nces.ed.gov,18,170,"Agriculture, Food, and Natural Resources",True
    2A52F377-0668-432C-BAB3-47669DDBFAA8,RefAcademicSubject,nces.ed.gov,19,180,Human Services,True
    F183FE55-3189-4DA0-8FCF-8B027DD3FFD9,RefAcademicSubject,nces.ed.gov,20,190,"Transportation, Distribution and Logistics",True
    2A7AC5E0-638E-4C56-A9B1-0EA0C4C068E8,RefAcademicSubject,nces.ed.gov,21,200,Engineering and Technology,True
    B0095617-E1D0-4ADC-B07D-E96D06FFEEFB,RefAcademicSubject,nces.ed.gov,22,210,Miscellaneous,True
    FC893BDD-3B3F-40F8-BD0E-921B4B7555D6,RefAcademicSubject,nces.ed.gov,23,220,Non-Subject-Specific,True
    E937C1C2-398F-4DC2-A76A-0B39F3441311,RefAcademicSubject,nces.ed.gov,24,230,World Languages,True
    F4DF5BDD-6698-4BB9-BC06-AA91325DDB3B,RefOrgType,microsoft.com,municipality,130,Municipality,True
    8180C51D-59D8-42F5-B283-5F73CCDFE71E,RefOrgType,microsoft.com,academicTrust,140,Academic Trust,True
    AB328F3A-329D-46B2-89FE-04558D5F3C17,RefOrgType,microsoft.com,localAuthority,150,Local Authority,True
    A8AAFD43-8EC5-4E23-B4E4-F5FEBCD4EB23,RefOrgType,microsoft.com,region,160,Region,True
    2432F831-58B0-4418-89DA-3AFB83CAA406,RefOrgType,microsoft.com,division,170,Division,True
    E5F64566-42B1-4170-91ED-9095A7AABDF8,RefOrgType,microsoft.com,province,180,Province,True
    A7B552AB-5FEE-4106-A82A-B104AD802243,RefOrgType,microsoft.com,researchCenter,190,Research Center,True
    4A7A8BDF-CE07-4CF2-A774-061EE8814FB9,RefOrgType,microsoft.com,program,200,Program,True
    BBDFDE11-F33A-4552-B070-0FEF5786E08F,RefStaffOrgRole,microsoft.com,professor,150,professor,True
    23CD21F1-9932-4EED-BD5C-EE99A6C57B31,RefStaffOrgRole,microsoft.com,researcher,160,researcher,True
    2A92CC07-161E-497D-8807-249F6A20948F,RefStaffOrgRole,microsoft.com,lecturer,170,lecturer,True
    11DE2FAC-CAB6-4726-9462-1C3D91091429,RefStaffOrgRole,microsoft.com,affiliate,180,affiliate,True
    DB0D832C-AA17-4F43-AB2B-92562DF9EF11,RefStaffOrgRole,microsoft.com,adjunct,190,adjunct,True
    865BC785-449E-4F0C-A72B-3F8553D83F8A,RefStaffOrgRole,microsoft.com,alumni,200,alumni,True
    845C489B-2A41-4A8E-B118-3080AD568418,RefStaffOrgRole,microsoft.com,instructor,210,instructor,True
    75A1395F-CD88-4362-BE34-0AB54235F24C,RefStaffOrgRole,microsoft.com,chair,220,chair,True
    583A3E66-878F-44E7-BBA3-1146C1BC5B2B,RefStaffOrgRole,microsoft.com,advisor,230,advisor,True
    4D023BD0-FB4B-40D4-9C66-5995B1A765A6,RefStaffOrgRole,microsoft.com,faculty,240,faculty,True
    0639C0E4-D351-42EF-92B4-8BD1CF27CA41,RefStaffOrgRole,microsoft.com,substitute,250,substitute,True
    68294947-AA84-4D64-A9A3-16CBB1187E21,RefStaffOrgRole,microsoft.com,principal,260,principal,True
    9D95BE64-81F1-49FA-8CC8-A93DD49B218F,RefStaffOrgRole,microsoft.com,specialServices,270,Special services,True
    75A382BB-904C-461D-BE61-EDC0516B39D6,RefStaffSectionRole,microsoft.com,professor,120,professor,True
    5742E90C-3600-4026-B014-3E0FFA5AC64C,RefStaffSectionRole,microsoft.com,researcher,130,researcher,True
    08913527-F988-46E5-861A-A9C64A598CB5,RefStaffSectionRole,microsoft.com,lecturer,140,lecturer,True
    8D939A14-7077-4A4A-88B5-ADB3C251BF17,RefStaffSectionRole,microsoft.com,affiliate,150,affiliate,True
    6482B3B0-5A5C-4A32-820A-1749B323F9A9,RefStaffSectionRole,microsoft.com,adjunct,160,adjunct,True
    65FB1E06-4E0C-4D69-8281-B1DD664FDF02,RefStaffSectionRole,microsoft.com,instructor,170,instructor,True
    FDA194DD-3EBA-48AE-8ACE-83CE0A59C647,RefStaffSectionRole,microsoft.com,advisor,180,advisor,True
    9C15F8C6-4287-4AF2-97C4-9A8AD1BE331E,RefStaffSectionRole,microsoft.com,faculty,190,faculty,True
    75F91BF4-9816-4F36-8EC3-07EED1EE246E,RefStaffSectionRole,microsoft.com,substitute,200,substitute,True
    15B67274-8286-4874-818B-AA361785B72D,RefStaffSectionRole,microsoft.com,principal,210,principal,True
    6818DAAB-EBC6-4E3D-8DDE-2872F056F4B4,RefStaffSectionRole,microsoft.com,specialServices,220,Special services,True
    9D829C49-EF4F-482C-AC37-10974F500889,RefGradeLevel,microsoft.com,PS1,220,Postsecondary freshman,True
    72C52CC1-09B0-4F83-822C-3E6B41373250,RefGradeLevel,microsoft.com,PS2,230,Postsecondary sophomore,True
    82C10216-45D1-4754-9B65-91906F220D97,RefGradeLevel,microsoft.com,PS3,240,Postsecondary junior,True
    941D916E-900F-4AAE-862A-A37203ABB1CB,RefGradeLevel,microsoft.com,PS4,250,Postsecondary senior,True
    85149F2C-769C-40CE-9CC8-A8F999291899,RefGradeLevel,microsoft.com,undergraduate,260,undergraduate,True
    85CF8FA2-B882-4B58-8886-6AE741C4F5C7,RefGradeLevel,microsoft.com,graduate,270,graduate,True
    3C9654D0-496E-421B-AC5B-41AF7A35EE7A,RefGradeLevel,microsoft.com,postgraduate,280,Graduate with an emphasis on research,True
    CFEAC234-B304-49C4-B814-5448AC3A8FFD,RefGradeLevel,microsoft.com,alumni,290,alumni,True
    BC7BD092-C3C1-4FAC-B82B-3D074DF4C832,RefGradeLevel,microsoft.com,adultEducation,300,Adult Education,True"""